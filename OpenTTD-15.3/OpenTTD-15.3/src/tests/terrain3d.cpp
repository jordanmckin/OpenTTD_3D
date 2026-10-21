/* This file is part of OpenTTD and is licensed under the GNU General Public License version 2. */
#include "../stdafx.h"
#include "../3rdparty/catch2/catch.hpp"
#include "../video/terrain3d_math.h"
#include "../video/terrain3d_mesh.h"
#include "../video/terrain3d_dirty.h"
#include "../video/terrain3d_cache.h"
#include "../video/terrain3d_slots.h"
#include "../video/rail3d_geometry.h"
#include "../video/asset3d_generated.h"
#include "../video/asset3d_art.h"
#include "../video/asset3d_lod.h"
#include "../video/vehicle3d_lod.h"
#include "../video/ground3d.h"
#include "../video/ground3d_textures.h"
#include "../track_func.h"
#include "../map_func.h"
#include "../landscape.h"
#include "../safeguards.h"

TEST_CASE("Heading yaw turns every vehicle direction straight up the screen")
{
	for (int direction = DIR_BEGIN; direction < DIR_END; ++direction) {
		float a = Terrain3D::HeadingYaw(direction) * 3.14159265f / 180;
		for (float tilt : {0.6f, 1.f, 1.6f}) {
			Terrain3D::Camera camera{0, 0, 1, 0, 0, std::cos(a), std::sin(a), tilt};
			auto delta = TileIndexDiffCByDir(static_cast<Direction>(direction));
			auto p = camera.Project({float(delta.x), float(delta.y), 0});
			CHECK(std::abs(p.x) < 0.0001f);
			CHECK(p.y < 0);
		}
	}
}

TEST_CASE("Orthographic pointer bounds retain sloped hits at every management angle and zoom")
{
	using Terrain3D::Vec;
	const std::array<Vec, 3> world{{{32, 48, 8}, {48, 48, 16}, {32, 64, 8}}};
	for (int yaw = 0; yaw < 360; yaw += 15) for (float tilt : {0.4f, 0.6f, 1.0f, 1.4f, 1.8f}) for (float scale : {0.25f, 1.0f, 4.0f}) {
		float a = yaw * 3.14159265359f / 180;
		Terrain3D::Camera camera{100, 90, scale, 800, 600, std::cos(a), std::sin(a), tilt, 24};
		std::array<Vec, 3> p{camera.Project(world[0]), camera.Project(world[1]), camera.Project(world[2])};
		Vec at{(world[0].x + world[1].x + world[2].x) / 3, (world[0].y + world[1].y + world[2].y) / 3, (world[0].z + world[1].z + world[2].z) / 3};
		auto screen = camera.Project(at);
		CHECK(Terrain3D::HitBox(camera, {32, 48, 8}, {48, 64, 16}, screen.x, screen.y));
		std::array<float, 3> weights;
		/* Some low angles see this exact slope edge-on: no triangle target then. */
		if (!Terrain3D::Hit(p, screen.x, screen.y, weights)) continue;
		Vec hit{};
		float depth = 0;
		for (int i = 0; i < 3; ++i) {
			hit.x += weights[i] * world[i].x; hit.y += weights[i] * world[i].y; hit.z += weights[i] * world[i].z;
			depth += weights[i] * p[i].z;
		}
		CHECK(hit.x == Approx(at.x).margin(0.02f));
		CHECK(hit.y == Approx(at.y).margin(0.02f));
		CHECK(hit.z == Approx(at.z).margin(0.02f));
		CHECK(depth == Approx(screen.z).margin(0.02f));
		CHECK_FALSE(Terrain3D::HitBox(camera, {32, 48, 8}, {48, 64, 16}, screen.x + 10000, screen.y));
	}
}

TEST_CASE("Perspective camera looks along its heading and culls behind it and beyond its draw distance")
{
	const Terrain3D::Vec eye{1000, 1000, 50};
	for (int direction = DIR_BEGIN; direction < DIR_END; ++direction) {
		auto along = [&](int dir, float length) {
			auto delta = TileIndexDiffCByDir(static_cast<Direction>(dir % DIR_END));
			float scale = length / std::sqrt(float(delta.x * delta.x + delta.y * delta.y));
			return std::array<float, 2>{delta.x * scale, delta.y * scale};
		};
		auto camera = Terrain3D::PerspectiveCamera(eye, Terrain3D::HeadingYaw(direction), 0, 60, 640, 480, 1024);
		REQUIRE(camera.Perspective());
		auto ahead = along(direction, 100), right = along(direction + 2, 20);
		Terrain3D::Vec target{eye.x + ahead[0], eye.y + ahead[1], eye.z};
		auto centre = camera.Project(target);
		CHECK(std::abs(centre.x - 320) < 0.01f);
		CHECK(std::abs(centre.y - 240) < 0.01f);
		auto p = camera.Project({target.x + right[0], target.y + right[1], target.z});
		CHECK(p.x > 330);
		CHECK(std::abs(p.y - 240) < 0.01f);
		CHECK(camera.Project({target.x, target.y, target.z + 20}).y < 230);
		auto nearer = along(direction, 50);
		CHECK(camera.Project({eye.x + nearer[0], eye.y + nearer[1], eye.z}).z > centre.z);
		auto box = [&](float distance) {
			auto c = along(direction, distance);
			return Terrain3D::Visible({eye.x + c[0] - 8, eye.y + c[1] - 8, 0}, {eye.x + c[0] + 8, eye.y + c[1] + 8, 60}, camera);
		};
		CHECK(box(100));
		CHECK(box(900));
		CHECK_FALSE(box(-100));
		CHECK_FALSE(box(1100));
		CHECK(Terrain3D::Visible({eye.x - 4, eye.y - 4, eye.z - 4}, {eye.x + 4, eye.y + 4, eye.z + 4}, camera));
	}
	/* Looking down puts the ground ahead below the centre of the screen. */
	auto down = Terrain3D::PerspectiveCamera(eye, 0, -20, 60, 640, 480, 1024);
	CHECK(down.Project({eye.x - 100, eye.y - 100, eye.z}).y < 240);
	CHECK(down.Project({eye.x - 100, eye.y - 100, eye.z - 100}).y > 240);
}

TEST_CASE("Chase camera trails its vehicle, turns gradually the short way and keeps it in view")
{
	using Terrain3D::ChaseTarget;
	for (int direction = DIR_BEGIN; direction < DIR_END; ++direction) {
		/* The eye sits behind and above the vehicle, which shows below the centre of the screen. */
		ChaseTarget at{2000, 2000, 40, Terrain3D::HeadingYaw(direction)};
		auto e = Terrain3D::ChaseEye(at, 0);
		auto camera = Terrain3D::PerspectiveCamera({e[0], e[1], e[2]}, e[3], e[4], e[5], 640, 480, 1024);
		auto vehicle = camera.Project({at.x, at.y, at.z});
		CHECK(std::abs(vehicle.x - 320) < 0.5f);
		CHECK(vehicle.y > 240);
		CHECK(vehicle.y < 480);
		CHECK(std::abs(std::hypot(e[0] - at.x, e[1] - at.y) - Terrain3D::CHASE_BACK) < 0.01f);
		CHECK(e[2] == at.z + Terrain3D::CHASE_UP);
		CHECK(Terrain3D::ChaseEye(at, 100)[2] == 100 + Terrain3D::CHASE_CLEARANCE);
	}
	/* A 45 degree turn eases over several frames instead of snapping, and goes the short way across north. */
	auto still = [](ChaseTarget t) { return Terrain3D::ChaseFollow{t, t}; };
	Terrain3D::ChaseFollow follow = still({0, 0, 0, 350});
	ChaseTarget target{0, 0, 0, 35};
	float previous = 350;
	for (int frame = 0; frame < 240; ++frame) {
		follow = Terrain3D::FollowChase(follow, target, 1, 1 / 60.0f);
		float step = std::abs(std::remainder(follow.smooth.heading - previous, 360.0f));
		CHECK(step < 2.0f);
		previous = follow.smooth.heading;
	}
	CHECK(std::abs(std::remainder(follow.smooth.heading - 35, 360.0f)) < 2.0f);
	/* Distance travelled turns it too, so a fast vehicle does not run away from its camera on a curve, up to the turn rate. */
	auto turned = Terrain3D::FollowChase(still({0, 0, 0, 0}), {0, -40, 0, 90}, 5, 0.1f).smooth.heading;
	CHECK(std::abs(turned - Terrain3D::CHASE_TURN_RATE * 0.1f) < 0.01f);
	/* Position trails by at most the lag, and settles exactly. */
	auto moved = Terrain3D::FollowChase(still({0, 0, 0, 0}), {40, 0, 0, 0}, 5, 0);
	CHECK(moved.smooth.x == 40 - Terrain3D::CHASE_LAG);
	follow = still({0, 0, 0, 0});
	for (int frame = 0; frame < 600; ++frame) follow = Terrain3D::FollowChase(follow, {10, -10, 5, 90}, 1, 1 / 60.0f);
	CHECK(follow == still({10, -10, 5, 90}));
	/* A train reversing puts its lead vehicle at the other end of the train in one tick, facing the other way: the camera
	 * slides and swings round over several frames instead of jumping with it. */
	follow = still({0, 0, 0, 0});
	ChaseTarget reversed{0, 80, 0, 180};
	auto eye = Terrain3D::ChaseEye(follow.smooth, 0);
	for (int frame = 0; frame < 600; ++frame) {
		follow = Terrain3D::FollowChase(follow, reversed, frame == 0 ? 1 : 0, 1 / 60.0f);
		auto next = Terrain3D::ChaseEye(follow.smooth, 0);
		CHECK(std::hypot(next[0] - eye[0], next[1] - eye[1]) < 8);
		eye = next;
	}
	CHECK(follow == still(reversed));
	/* A long jump starts again at the vehicle. */
	CHECK(Terrain3D::FollowChase(still({0, 0, 0, 0}), {500, 0, 0, 180}, 1, 0.01f) == still({500, 0, 0, 180}));
}

TEST_CASE("Cab camera sits on the front of its vehicle, sees the line ahead and tips with slopes")
{
	using Terrain3D::ChaseTarget;
	constexpr float ahead = 6, up = 5;
	for (int direction = DIR_BEGIN; direction < DIR_END; ++direction) {
		ChaseTarget at{2000, 2000, 40, Terrain3D::HeadingYaw(direction)};
		auto e = Terrain3D::CabEye(at, ahead, up);
		auto forward = Terrain3D::HeadingForward(at.heading);
		CHECK(std::abs(std::hypot(e[0] - at.x, e[1] - at.y) - ahead) < 0.01f);
		CHECK(std::abs((e[0] - at.x) * forward[0] + (e[1] - at.y) * forward[1] - ahead) < 0.01f);
		CHECK(e[2] == at.z + up);
		auto camera = Terrain3D::PerspectiveCamera({e[0], e[1], e[2]}, e[3], e[4], e[5], 640, 480, 1024);
		/* The vehicle's own position is behind the eye, so nothing of it near its centre is drawn. */
		CHECK_FALSE(Terrain3D::Visible({at.x - 1, at.y - 1, at.z}, {at.x + 1, at.y + 1, at.z + 2}, camera));
		/* The track half a tile in front of the cab is on screen, centred, and so is the line two tiles on, higher up. */
		for (float distance : {8.0f, 32.0f}) {
			auto p = camera.Project({e[0] + forward[0] * distance, e[1] + forward[1] * distance, at.z});
			CHECK(std::abs(p.x - 320) < 0.5f);
			CHECK(p.y > 240);
			CHECK(p.y < 480);
		}
	}
	/* On a slope the eye rises with the front of the vehicle and looks along the slope. */
	float grade = std::atan2(8.0f, 16.0f) * 180 / 3.14159265359f;
	ChaseTarget climbing{0, 0, 40, 90, grade};
	auto e = Terrain3D::CabEye(climbing, ahead, up);
	CHECK(std::abs(e[2] - (40 + up + ahead / 2)) < 0.01f);
	CHECK(std::abs(e[4] - (Terrain3D::CAB_PITCH + grade)) < 0.01f);
	auto camera = Terrain3D::PerspectiveCamera({e[0], e[1], e[2]}, e[3], e[4], e[5], 640, 480, 1024);
	auto forward = Terrain3D::HeadingForward(90);
	auto slope = camera.Project({forward[0] * 32, forward[1] * 32, 40 + 16});
	CHECK(slope.y > 240);
	CHECK(slope.y < 480);
	/* Through a curve the heading and the grade turn within about a tile travelled, a few degrees a frame at most. */
	auto still = [](ChaseTarget t) { return Terrain3D::ChaseFollow{t, t}; };
	auto follow = still({0, 0, 0, 0});
	float heading = 0, tipped = 0;
	for (int frame = 1; frame <= 40; ++frame) {
		follow = Terrain3D::FollowChase(follow, {-float(frame), 0, 0, 45, grade}, 1, 1 / 60.0f, Terrain3D::CAB_TIMING);
		CHECK(std::abs(follow.smooth.heading - heading) <= Terrain3D::CAB_TIMING.turn_rate / 60 + 0.01f);
		CHECK(std::abs(follow.smooth.grade - tipped) <= Terrain3D::CAB_TIMING.turn_rate / 60 + 0.01f);
		heading = follow.smooth.heading;
		tipped = follow.smooth.grade;
	}
	CHECK(std::abs(heading - 45) < 2);
	CHECK(std::abs(tipped - grade) < 2);
	/* Position only smooths the steps between ticks, staying on the vehicle. */
	CHECK(Terrain3D::FollowChase(still({0, 0, 0, 0}), {40, 0, 0, 0}, 5, 0, Terrain3D::CAB_TIMING).smooth.x == 40 - Terrain3D::CAB_TIMING.lag);
	/* A train reversing hands the cab to the other end at once, facing the other way. */
	CHECK(Terrain3D::FollowChase(still({0, 0, 0, 0}), {0, 80, 0, 180}, 1, 1 / 60.0f, Terrain3D::CAB_TIMING) == still({0, 80, 0, 180}));
}

TEST_CASE("Ride-along views fade to black into a tunnel and back in after it")
{
	using Terrain3D::TunnelDark;
	constexpr float frame = 1 / 60.0f;
	/* Heading in, the view darkens with distance and is black when the eye reaches the hiding point, at any speed. */
	float dark = 0, last = 0;
	for (float to_go = 12; to_go >= 0; to_go -= 0.5f) {
		dark = TunnelDark(dark, false, to_go, frame);
		CHECK(dark >= last);
		last = dark;
	}
	CHECK(dark == 1);
	CHECK(TunnelDark(0, false, Terrain3D::TUNNEL_FADE_DISTANCE, frame) == 0);
	CHECK(TunnelDark(0, false, Terrain3D::TUNNEL_FADE_DISTANCE / 2, 0) == 0.5f);
	/* Hidden in the tunnel it stays black, even far from the portal. */
	for (int i = 0; i < 120; ++i) dark = TunnelDark(dark, true, -1, frame);
	CHECK(dark == 1);
	/* A view that sees the vehicle hide without a distance to go (on a curve) still goes black, over a short time. */
	float hid = TunnelDark(0, true, -1, Terrain3D::TUNNEL_FADE_OUT_TIME / 2);
	CHECK(hid > 0.4f);
	CHECK(hid < 0.6f);
	CHECK(TunnelDark(hid, true, -1, Terrain3D::TUNNEL_FADE_OUT_TIME) == 1);
	/* Out again, it fades in over TUNNEL_FADE_IN_TIME, steadily, and is clear afterwards. */
	int frames = 0;
	for (last = dark; dark > 0; ++frames) {
		dark = TunnelDark(dark, false, -1, frame);
		CHECK(dark < last);
		CHECK(last - dark <= frame / Terrain3D::TUNNEL_FADE_IN_TIME + 0.001f);
		last = dark;
	}
	CHECK(std::abs(frames - Terrain3D::TUNNEL_FADE_IN_TIME * 60) <= 1);
	CHECK(TunnelDark(0, false, -1, frame) == 0);
	/* A stalled frame does not skip the fade in. */
	CHECK(TunnelDark(1, false, -1, 0.5f) == 0.75f);
}

TEST_CASE("Distant library LOD bounds displacement through rotation, tilt and stretched vehicles")
{
	CHECK_FALSE(Terrain3D::ModelLODAllowed(0.1f, 4, 5, 1, 1, 1));
	CHECK(Terrain3D::ModelLODAllowed(0.2f, 4, 5, 0.5f, 1, 1));
	CHECK_FALSE(Terrain3D::ModelLODAllowed(0.4f, 4, 5, 0.5f, 1, 1));
	CHECK_FALSE(Terrain3D::ModelLODAllowed(0.2f, 4, 5, 0.5f, 1, 2));
	CHECK_FALSE(Terrain3D::ModelLODAllowed(0.01f, 100, 5, 0.5f, 1, 1));
	for (float tilt : {0.6f, 1.f, 1.4f, 3.f}) for (float length : {0.5f, 1.f, 2.f}) {
		for (int yaw = 0; yaw < 360; yaw += 15) for (int direction = 0; direction < 360; direction += 30) {
			float a = yaw * 3.14159265f / 180, b = direction * 3.14159265f / 180;
			Terrain3D::Camera camera{0, 0, 0.25f, 0, 0, std::cos(a), std::sin(a), tilt};
			float limit = Terrain3D::ModelPixelScale(camera.scale, tilt, length);
			for (auto delta : {Terrain3D::Vec{1, 0, 0}, Terrain3D::Vec{0, 1, 0}, Terrain3D::Vec{0, 0, 1}, Terrain3D::Vec{.6f, .8f, 0}}) {
				auto p = camera.Project({delta.x * length * std::cos(b) - delta.y * std::sin(b), delta.x * length * std::sin(b) + delta.y * std::cos(b), delta.z});
				CHECK(std::hypot(p.x, p.y) <= limit + 0.00001f);
			}
		}
	}
}

TEST_CASE("Generated LOD meshes retain bounds, materials and valid library references")
{
	REQUIRE(std::size(ArtLOD3D::levels) == std::size(Art3D::models));
	size_t reductions = 0;
	for (size_t i = 0; i < std::size(ArtLOD3D::levels); ++i) {
		const auto &full = Art3D::models[i];
		for (const auto &level : ArtLOD3D::levels[i].level) {
			if (level.model == 0xFFFF) continue;
			++reductions;
			REQUIRE(level.model < std::size(ArtLOD3D::models));
			const auto &reduced = ArtLOD3D::models[level.model];
			REQUIRE(reduced.count > 0);
			CHECK(reduced.count < full.count);
			CHECK((level.error > 0 && std::isfinite(level.error)));
			std::array<float, 6> bounds[2];
			std::set<std::array<float, 3>> colours[2];
			for (int m = 0; m < 2; ++m) {
				bounds[m] = {1e30f, 1e30f, 1e30f, -1e30f, -1e30f, -1e30f};
				const auto &model = m == 0 ? full : reduced;
				for (size_t f = 0; f < model.count; ++f) {
					const auto &face = model.faces[f];
					colours[m].insert({face.colour[0], face.colour[1], face.colour[2]});
					for (const auto &p : face.p) for (int k = 0; k < 3; ++k) {
						REQUIRE(std::isfinite(p[k]));
						bounds[m][k] = std::min(bounds[m][k], p[k]);
						bounds[m][k + 3] = std::max(bounds[m][k + 3], p[k]);
					}
					float ax = face.p[1][0] - face.p[0][0], ay = face.p[1][1] - face.p[0][1], az = face.p[1][2] - face.p[0][2];
					float bx = face.p[2][0] - face.p[0][0], by = face.p[2][1] - face.p[0][1], bz = face.p[2][2] - face.p[0][2];
					CHECK(std::hypot(ay*bz-az*by, az*bx-ax*bz, ax*by-ay*bx) >= 0.000099f);
				}
			}
			CHECK(bounds[0] == bounds[1]);
			CHECK(colours[0] == colours[1]);
		}
	}
	CHECK(reductions > 0);
}

TEST_CASE("3D asset registry resolves base identities and rejects unknown content")
{
	CHECK(Asset3D::House(0)==Asset3D::OFFICE);
	CHECK(Asset3D::House(6)==Asset3D::HOUSE0);
	CHECK(Asset3D::House(4095)==Asset3D::MISSING);
	CHECK(Asset3D::Industry(0,0)==Asset3D::MINE_HEAD);
	CHECK(Asset3D::Industry(1,8)==Asset3D::POWER_STACK);
	CHECK(Asset3D::Industry(1,0)==Asset3D::MISSING);
	CHECK(Asset3D::Industry(99,0)==Asset3D::MISSING);
	for (const auto &model:Asset3D::models) {
		REQUIRE(model.count>0);
		CHECK(model.count<600);
		for (size_t i=0;i<model.count;++i) {
			const auto &f=model.faces[i];
			for (const auto &p:f.p) for (float v:p) CHECK(std::isfinite(v));
			for (float c:f.colour) CHECK((c>=0 && c<=1));
			float ax=f.p[1][0]-f.p[0][0],ay=f.p[1][1]-f.p[0][1],az=f.p[1][2]-f.p[0][2];
			float bx=f.p[2][0]-f.p[0][0],by=f.p[2][1]-f.p[0][1],bz=f.p[2][2]-f.p[0][2];
			CHECK(std::abs(ay*bz-az*by)+std::abs(az*bx-ax*bz)+std::abs(ax*by-ay*bx)>0.00001f);
		}
	}
}

TEST_CASE("Phase 8 art table references valid models and falls back for unknown identities")
{
	CHECK(Art3D::House(4095,3)==-1);
	CHECK(Art3D::Engine(0xFFFE,false)==-1);
	CHECK(Art3D::Tree(0xFF,3)==-1);
	CHECK(Art3D::IndustryTile(0xFFFE,3)==-1);
	for (const auto *table : {&Art3D::houses[0], &Art3D::industry_tiles[0], &Art3D::engines[0], &Art3D::trees[0]}) {
		if (table->id==0xFFFF) continue;
		CHECK(table->model<std::size(Art3D::models));
	}
	for (const auto &e : Art3D::engines) if (e.id!=0xFFFF) CHECK(Art3D::Engine(e.id,e.state==1)>=0);
	/* Rail furniture: signals are variant * 8 + SignalType, the level crossing is 16 and the catenary pieces 17; aspects never substitute for each other. */
	for (const auto &e : Art3D::furniture) {
		if (e.id==0xFFFF) continue;
		CHECK(e.model<std::size(Art3D::models));
		if (e.id<16) CHECK(Art3D::Signal(e.id>>3,e.id&7,e.state==1)==e.model);
		else if (e.id==16) CHECK(Art3D::Crossing(e.state==1)==e.model);
		else CHECK(Art3D::Catenary(e.state)==e.model);
	}
	CHECK(Art3D::Signal(0,7,true)==-1);
	for (const auto &model:Art3D::models) {
		for (size_t i=0;i<model.count;++i) {
			const auto &f=model.faces[i];
			for (const auto &p:f.p) for (float v:p) CHECK(std::isfinite(v));
			/* Company colour markers are -1 and -2; glowing colours are stored plus 2. */
			bool glow=f.colour[0]>1.5f;
			for (float c:f.colour) CHECK(((c>=(glow?2:0) && c<=(glow?3:1)) || c==-1 || c==-2));
		}
	}
}

TEST_CASE("Phase 8 ground layers cover every ground state and match the embedded textures")
{
	using Ground3D::Kind;
	STATIC_REQUIRE(Ground3D::TEXTURE_LAYERS==Ground3D::LAYER_COUNT);
	STATIC_REQUIRE(Ground3D::LAYER_COUNT<Ground3D::NO_BLEND);
	CHECK(std::string_view(Ground3D::layer_names[Ground3D::GRASS_0])=="grass_0");
	CHECK(std::string_view(Ground3D::layer_names[Ground3D::FIELD_8])=="field_8");
	CHECK(std::string_view(Ground3D::layer_names[Ground3D::SNOW_3])=="snow_3");
	CHECK(std::string_view(Ground3D::layer_names[Ground3D::CONCRETE])=="concrete");
	for (unsigned d=0;d<4;++d) {
		CHECK(Ground3D::LayerOf(Kind::Grass,d)==Ground3D::GRASS_0+d);
		CHECK(Ground3D::LayerOf(Kind::Snow,d)==Ground3D::SNOW_0+d);
		CHECK(Ground3D::LayerOf(Kind::Desert,d)==Ground3D::DESERT_0+d);
	}
	CHECK(Ground3D::LayerOf(Kind::Grass,7)==Ground3D::GRASS_3);
	for (unsigned f=0;f<=8;++f) CHECK(Ground3D::LayerOf(Kind::Fields,3,f)==Ground3D::FIELD_0+f);
	CHECK(Ground3D::LayerOf(Kind::Fields,3,15)==Ground3D::FIELD_0);
	for (const auto &mean : Ground3D::average) for (float c : mean) CHECK((c>=0 && c<=1));
	/* Water and snow must stay distinguishable from grass in the flat fallback. */
	CHECK(Ground3D::average[Ground3D::WATER][2]>Ground3D::average[Ground3D::WATER][1]);
	CHECK(Ground3D::average[Ground3D::SNOW_3][0]>Ground3D::average[Ground3D::GRASS_3][0]+0.3f);
	CHECK(std::size(Ground3D::texels)==size_t(Ground3D::TEXTURE_LAYERS)*Ground3D::TEXTURE_SIZE*Ground3D::TEXTURE_SIZE);
}

TEST_CASE("3D bridge ramps agree with engine slope pixel heights in all directions")
{
	const Slope slopes[]={SLOPE_NE,SLOPE_SE,SLOPE_SW,SLOPE_NW};
	for (int dir=0;dir<4;++dir) for (int base : {0,8,40}) {
		for (int y=0;y<16;++y) for (int x=0;x<16;++x) {
			CHECK(std::abs(Rail3D::RampHeight(dir,true,base,float(x),float(y))-(base+GetPartialPixelZ(x,y,slopes[dir])))<=0.5f);
			CHECK(Rail3D::RampHeight(dir,false,base,float(x),float(y))==base+TILE_HEIGHT);
		}
		CHECK(Rail3D::RampHeight(dir,true,base,Rail3D::EDGES[dir][0],Rail3D::EDGES[dir][1])==base+TILE_HEIGHT);
		CHECK(Rail3D::RampHeight(dir,true,base,Rail3D::EDGES[(dir+2)%4][0],Rail3D::EDGES[(dir+2)%4][1])==base);
	}
}

TEST_CASE("3D rail endpoints agree with authoritative track directions")
{
	for (Track track=TRACK_BEGIN;track<TRACK_END;track++) {
		auto forward=TrackToTrackdir(track);
		auto reverse=ReverseTrackdir(forward);
		int a=Rail3D::PATHS[track][0],b=Rail3D::PATHS[track][1];
		CHECK(a!=b);
		CHECK(((a==TrackdirToExitdir(forward) && b==TrackdirToExitdir(reverse)) ||
				(b==TrackdirToExitdir(forward) && a==TrackdirToExitdir(reverse))));
	}
}

TEST_CASE("3D diagonal rail strip edges meet across neighbouring tiles")
{
	/* Check both physical rails and both ballast edges, not just centrelines. */
	for (float side : {-3.1f, -1.9f, -1.3f, 1.3f, 1.9f, 3.1f}) {
		auto same = [](auto a, auto b, float x, float y) {
			CHECK(a[0] == Approx(b[0] + x));
			CHECK(a[1] == Approx(b[1] + y));
		};
		same(Rail3D::StripPoint(TRACK_UPPER, 0, side), Rail3D::StripPoint(TRACK_LOWER, 0, -side), -16, 0);
		same(Rail3D::StripPoint(TRACK_UPPER, 1, side), Rail3D::StripPoint(TRACK_LOWER, 1, -side), 0, -16);
		same(Rail3D::StripPoint(TRACK_LEFT, 1, side), Rail3D::StripPoint(TRACK_RIGHT, 0, side), 16, 0);
		same(Rail3D::StripPoint(TRACK_LEFT, 0, side), Rail3D::StripPoint(TRACK_RIGHT, 1, side), 0, -16);
		for (int track = 0; track < 6; ++track) for (int i = 0; i <= 8; ++i) {
			auto p = Rail3D::StripPoint(track, i / 8.0f, side);
			CHECK((p[0] >= 0 && p[0] <= 16 && p[1] >= 0 && p[1] <= 16));
			const auto &a = Rail3D::EDGES[Rail3D::PATHS[track][0]], &b = Rail3D::EDGES[Rail3D::PATHS[track][1]];
			float dx = b[0] - a[0], dy = b[1] - a[1];
			CHECK(((p[1] - a[1]) * dx - (p[0] - a[0]) * dy) / std::hypot(dx, dy) == Approx(side));
		}
	}
}

TEST_CASE("3D train heading follows engine world direction deltas")
{
	for (Direction direction=DIR_BEGIN;direction<DIR_END;direction++) {
		auto delta=TileIndexDiffCByDir(direction);
		auto heading=Rail3D::DIRECTIONS[direction];
		float length=std::hypot(float(delta.x),float(delta.y));
		CHECK(heading[0]==Approx(delta.x/length));
		CHECK(heading[1]==Approx(delta.y/length));
	}
}

TEST_CASE("3D classic projection matches OpenTTD affine coordinates")
{
	Terrain3D::Camera camera{0,0,4,0,0,1,0,1};
	for (auto p : {Terrain3D::Vec{16,32,8}, {0,0,0}, {512,256,96}}) {
		auto screen=camera.Project(p);
		CHECK(screen.x==Approx(8*(p.y-p.x)));
		CHECK(screen.y==Approx(4*(p.x+p.y-p.z)));
	}
}

TEST_CASE("3D picking interpolates sloped triangles under rotation tilt and zoom")
{
	std::array<Terrain3D::Vec,3> world{{{32,32,8},{48,32,16},{40,40,8}}};
	for (float yaw : {0.0f,0.7f,1.5707963f,3.1415926f,4.712389f}) for (float tilt : {0.4f,1.0f,1.8f}) for (float scale : {0.25f,1.0f,4.0f}) {
		Terrain3D::Camera camera{128,192,scale,1280,720,std::cos(yaw),std::sin(yaw),tilt};
		std::array<Terrain3D::Vec,3> projected{camera.Project(world[0]),camera.Project(world[1]),camera.Project(world[2])};
		auto expected=camera.Project({40.0f,36.8f,9.6f}); // weights 0.2, 0.2, 0.6
		std::array<float,3> weights;
		REQUIRE(Terrain3D::Hit(projected,expected.x,expected.y,weights));
		CHECK(weights[0]==Approx(0.2f).margin(0.001f));
		CHECK(weights[1]==Approx(0.2f).margin(0.001f));
		CHECK(weights[2]==Approx(0.6f).margin(0.001f));
	}
}

TEST_CASE("3D orbit pivot keeps the classic view and the centred ground point")
{
	/* Any pivot on the classic centre ray is invisible at yaw 0, tilt 1. */
	Terrain3D::Camera ground{100,140,2,640,480,1,0,1};
	Terrain3D::Camera raised{100+24,140+24,2,640,480,1,0,1,48};
	for (auto p : {Terrain3D::Vec{16,32,8}, {130,170,40}, {512,256,96}}) {
		CHECK(raised.Project(p).x==Approx(ground.Project(p).x));
		CHECK(raised.Project(p).y==Approx(ground.Project(p).y));
	}
	/* The pivot stays at the screen centre at every orbit angle. */
	for (float yaw : {0.0f,0.7f,2.4f,4.712389f}) for (float tilt : {0.4f,1.0f,1.8f}) {
		Terrain3D::Camera camera{124,164,2,640,480,std::cos(yaw),std::sin(yaw),tilt,48};
		auto centre=camera.Project({124,164,48});
		CHECK(centre.x==Approx(320));
		CHECK(centre.y==Approx(240));
	}
}

TEST_CASE("3D orbit scroll moves the rotated view by the requested screen delta")
{
	for (float yaw : {0.0f,0.7f,1.5707963f,3.1415926f,5.5f}) for (float tilt : {0.4f,1.0f,1.8f}) {
		auto delta=Terrain3D::ClassicScrollDelta(30,-12,std::cos(yaw),std::sin(yaw),tilt);
		/* A classic scroll (sx, sy) moves the world pivot by x = (sy - sx/2)/2, y = (sy + sx/2)/2. */
		float wx=(delta[1]-delta[0]/2)/2, wy=(delta[1]+delta[0]/2)/2;
		Terrain3D::Camera camera{0,0,1,0,0,std::cos(yaw),std::sin(yaw),tilt};
		auto moved=camera.Project({wx,wy,0});
		CHECK(moved.x==Approx(30).margin(0.001f));
		CHECK(moved.y==Approx(-12).margin(0.001f));
	}
	auto classic=Terrain3D::ClassicScrollDelta(30,-12,1,0,1);
	CHECK(classic[0]==Approx(30));
	CHECK(classic[1]==Approx(-12));
}

TEST_CASE("3D picking rejects outside and degenerate triangles")
{
	std::array<float,3> w;
	CHECK_FALSE(Terrain3D::Hit({{{0,0,0},{16,0,0},{0,16,8}}},20,20,w));
	CHECK_FALSE(Terrain3D::Hit({{{0,0,0},{1,1,0},{2,2,8}}},1,1,w));
}

TEST_CASE("3D chunk culling retains intersection and raised rotated terrain")
{
	Terrain3D::Camera camera{0,0,1,100,100,1,0,1};
	CHECK(Terrain3D::Visible({-16,-16,0},{16,16,8},camera));
	CHECK_FALSE(Terrain3D::Visible({1000,1000,0},{1016,1016,8},camera));
	CHECK(Terrain3D::Visible({0,0,0},{1000,1000,8},camera));
	CHECK(Terrain3D::Visible({40,40,64},{56,56,96},camera));
	camera.cosine=0; camera.sine=1;
	CHECK(Terrain3D::Visible({-16,-16,0},{16,16,32},camera));
	CHECK_FALSE(Terrain3D::Visible({1000,1000,0},{1016,1016,8},camera));
}

TEST_CASE("3D dirty corners cover adjacent chunks and remain inside the map")
{
	for (int size : {16, 32}) {
		CHECK(Terrain3D::DirtyChunks(size, size, 128, 64, size) == std::array<int, 4>{0, 0, 1, 1});
		CHECK(Terrain3D::DirtyChunks(size - 1, size - 1, 128, 64, size) == std::array<int, 4>{0, 0, 1, 1});
		CHECK(Terrain3D::DirtyChunks(0, 0, 128, 64, size) == std::array<int, 4>{0, 0, 0, 0});
		CHECK(Terrain3D::DirtyChunks(127, 63, 128, 64, size) == std::array<int, 4>{128 / size - 1, 64 / size - 1, 128 / size - 1, 64 / size - 1});
		CHECK(Terrain3D::DirtyChunks(4, 4, 128, 64, size) == std::array<int, 4>{0, 0, 0, 0});
	}
}

TEST_CASE("3D dirty tile snapshots coalesce shared corners edges reloads and chunk size changes")
{
	for (auto dimensions : {std::array<int, 2>{64, 64}, {35, 19}}) {
		int width = dimensions[0], height = dimensions[1];
		std::vector<int> world(width * height);
		/* Changing any corner affects neighboring derived snapshots. */
		auto authoritative = [&](int x, int y) {
			int value = 0;
			for (int ty = std::max(0, y - 1); ty <= std::min(height - 1, y + 1); ++ty)
				for (int tx = std::max(0, x - 1); tx <= std::min(width - 1, x + 1); ++tx) value += world[ty * width + tx];
			return value;
		};
		for (int size : {16, 32, 16}) {
			int nx = (width + size - 1) / size, ny = (height + size - 1) / size;
			std::vector<Terrain3D::DirtyTileSet> dirty(nx * ny);
			std::vector<std::vector<int>> snapshots(nx * ny);
			std::vector<bool> expected(width * height, true);
			uint32_t seed = 71;
			for (int step = 0; step < 40; ++step) {
				/* Include first use, same-sized reload, shared chunk edges, map edges,
				 * duplicate/no-op notifications, and multiple distant pending edits. */
				if (step == 20) {
					std::fill(world.begin(), world.end(), 0);
					dirty = std::vector<Terrain3D::DirtyTileSet>(nx * ny);
					snapshots = std::vector<std::vector<int>>(nx * ny);
					std::fill(expected.begin(), expected.end(), true);
				}
				for (int edit = 0; edit < 3; ++edit) {
					seed = seed * 1664525U + 1013904223U;
					int x = (seed >> 8) % width, y = (seed >> 16) % height;
					if (edit == 0) { x = std::min(width - 1, step); y = std::min(height - 1, step); }
					if (step % 3 != 0) ++world[y * width + x];
					for (int repeat = 0; repeat < 2; ++repeat) Terrain3D::MarkDirtyTiles(x, y, width, height, size,
						[&](int cx, int cy, size_t i) { dirty[cy * nx + cx].Mark(i); });
					/* Deliberately independent neighborhood expectation. */
					for (int ty = 0; ty < height; ++ty) for (int tx = 0; tx < width; ++tx)
						if (std::abs(tx - x) <= 1 && std::abs(ty - y) <= 1) expected[ty * width + tx] = true;
				}
				size_t reads = 0;
				for (int cy = 0; cy < ny; ++cy) for (int cx = 0; cx < nx; ++cx) {
					size_t index = cy * nx + cx;
					int cw = std::min(size, width - cx * size), ch = std::min(size, height - cy * size);
					auto before = snapshots[index];
					auto changed = dirty[index].Refresh(snapshots[index], cw * ch, false, [&](size_t i) {
						++reads;
						int x = cx * size + static_cast<int>(i % cw), y = cy * size + static_cast<int>(i / cw);
						CHECK(expected[y * width + x]);
						expected[y * width + x] = false;
						return authoritative(x, y);
					});
					CHECK(dirty[index].Empty());
					for (size_t i = 0; i < snapshots[index].size(); ++i) {
						CHECK(snapshots[index][i] == authoritative(cx * size + static_cast<int>(i % cw), cy * size + static_cast<int>(i / cw)));
						CHECK(changed[i] == (before.empty() || before[i] != snapshots[index][i]));
					}
					/* An independent full scan must still run on clean chunks. */
					size_t reference_reads = 0;
					auto reference = dirty[index].Refresh(snapshots[index], cw * ch, true, [&](size_t i) {
						++reference_reads;
						return authoritative(cx * size + static_cast<int>(i % cw), cy * size + static_cast<int>(i / cw));
						});
					CHECK(reference_reads == cw * ch);
					CHECK(std::count(reference.begin(), reference.end(), true) == 0);
				}
				CHECK(reads > 0);
				CHECK(std::count(expected.begin(), expected.end(), true) == 0);
			}
			/* A missed notification must be detected by the full-map reference. */
			++world[0];
			auto mismatch = dirty[0].Refresh(snapshots[0], size * std::min(size, height), true,
				[&](size_t i) { return authoritative(static_cast<int>(i % size), static_cast<int>(i / size)); });
			CHECK(std::count(mismatch.begin(), mismatch.end(), true) == 4);
		}
	}
}

TEST_CASE("3D packed tile meshes match full regeneration through growth removal and replacement")
{
	struct Face {
		std::array<Terrain3D::Vec, 3> p;
		bool operator==(const Face &) const = default;
	};
	std::vector<Face> faces, scratch;
	std::vector<Terrain3D::TileMeshSpan> spans;
	std::array<int, 16> sizes{}, heights{};
	auto build = [&](std::vector<Face> &out, size_t i) {
		for (int j = 0; j < sizes[i]; ++j) out.push_back({{{{float(i), 0, float(heights[i])}, {float(i), 1, float(j)}, {float(i + 1), 1, 0}}}});
	};
	uint32_t seed = 17;
	for (int step = 0; step < 100; ++step) {
		std::vector<bool> changed(sizes.size(), step == 0);
		/* Repeated edits include empty tiles, changing face counts, equal counts
		 * with different vertices, adjacent replacements and shrinking bounds. */
		for (int edit = 0; edit < 3; ++edit) {
			seed = seed * 1664525U + 1013904223U;
			size_t i = (seed >> 16) % sizes.size();
			changed[i] = true;
			sizes[i] = (seed >> 8) % 7;
			heights[i] = step % 9;
		}
		size_t builds = 0;
		Terrain3D::PatchTileMesh(faces, spans, changed, scratch, [&](auto &out, size_t i) { ++builds; build(out, i); });
		CHECK(builds == std::count(changed.begin(), changed.end(), true));
		std::vector<Face> reference;
		for (size_t i = 0; i < sizes.size(); ++i) {
			build(reference, i);
			CHECK(spans[i].end == reference.size());
			if (sizes[i] > 0) {
				CHECK(spans[i].low == Terrain3D::Vec{float(i), 0, 0});
				CHECK(spans[i].high == Terrain3D::Vec{float(i + 1), 1, float(std::max(heights[i], sizes[i] - 1))});
			} else {
				CHECK(spans[i].low.x > spans[i].high.x);
			}
		}
		CHECK(faces == reference);
	}
	/* Equal face counts with new vertices are written in place, without reallocating. */
	for (int step = 0; step < 20; ++step) {
		std::vector<bool> changed(sizes.size(), false);
		for (size_t i = step % 3; i < sizes.size(); i += 3) {
			changed[i] = true;
			heights[i] = 10 + step;
		}
		const Face *storage = faces.data();
		Terrain3D::PatchTileMesh(faces, spans, changed, scratch, build);
		CHECK(faces.data() == storage);
		std::vector<Face> reference;
		for (size_t i = 0; i < sizes.size(); ++i) {
			build(reference, i);
			CHECK(spans[i].end == reference.size());
			if (sizes[i] > 0) CHECK(spans[i].low.z == std::min(0.0f, float(heights[i])));
		}
		CHECK(faces == reference);
	}
	/* Updating a dense chunk must not transfer its large backing allocation to
	 * a sparse chunk when they share scratch storage. */
	std::vector<Face> dense, sparse;
	std::vector<Terrain3D::TileMeshSpan> dense_spans, sparse_spans;
	auto fill = [](auto &out, size_t count) { out.resize(count); };
	Terrain3D::PatchTileMesh(dense, dense_spans, {true}, scratch, [&](auto &out, size_t) { fill(out, 4096); });
	Terrain3D::PatchTileMesh(sparse, sparse_spans, {true}, scratch, [&](auto &out, size_t) { fill(out, 4); });
	Terrain3D::PatchTileMesh(dense, dense_spans, {false}, scratch, fill);
	Terrain3D::PatchTileMesh(sparse, sparse_spans, {false}, scratch, fill);
	CHECK(sparse.size() == 4);
	CHECK(sparse.capacity() < dense.size());
}

TEST_CASE("3D tile slots rewrite only changed tiles and keep the drawn buffer exact")
{
	/* Simulated GPU buffer: each vertex holds its tile and a version, so stale or overlapping slots show up. */
	const size_t tiles = 64;
	std::vector<size_t> sizes(tiles);
	std::vector<int> version(tiles, 0);
	for (size_t i = 0; i < tiles; ++i) sizes[i] = 3 * ((i * 7) % 5);
	Terrain3D::TileSlots slots;
	std::vector<std::pair<int, int>> buffer;
	std::vector<size_t> writes;
	auto apply = [&](const std::vector<bool> &changed) {
		bool whole = slots.Update(sizes, changed, writes);
		if (whole) buffer.assign(slots.size, {-1, -1});
		CHECK(buffer.size() == slots.size);
		for (size_t t : writes) for (int v = 0; v < slots.count[t]; ++v) buffer[slots.first[t] + v] = {int(t), version[t]};
		return whole;
	};
	auto verify = [&] {
		std::vector<std::pair<int, int>> occupied;
		for (size_t t = 0; t < tiles; ++t) {
			REQUIRE(slots.count[t] == int(sizes[t]));
			CHECK(slots.count[t] <= slots.capacity[t]);
			CHECK(slots.first[t] + slots.capacity[t] <= int(slots.used));
			for (int v = 0; v < slots.count[t]; ++v) CHECK(buffer[slots.first[t] + v] == std::pair<int, int>{int(t), version[t]});
			if (slots.capacity[t] > 0) occupied.push_back({slots.first[t], slots.first[t] + slots.capacity[t]});
		}
		CHECK(slots.used <= slots.size);
		std::sort(occupied.begin(), occupied.end());
		for (size_t i = 1; i < occupied.size(); ++i) CHECK(occupied[i - 1].second <= occupied[i].first);
		/* Merged runs draw exactly the tiles' vertices, in tile order. */
		std::vector<int> run_first, run_count, by_tile, by_run;
		slots.Runs(run_first, run_count);
		REQUIRE(run_first.size() == run_count.size());
		for (size_t t = 0; t < tiles; ++t) for (int v = 0; v < slots.count[t]; ++v) by_tile.push_back(slots.first[t] + v);
		for (size_t r = 0; r < run_first.size(); ++r) {
			CHECK(run_count[r] > 0);
			for (int v = 0; v < run_count[r]; ++v) by_run.push_back(run_first[r] + v);
		}
		CHECK(by_run == by_tile);
		return run_first.size();
	};
	CHECK(apply({}));
	CHECK(verify() == 1); // A packed buffer is drawn as one run.
	CHECK(slots.size == slots.used); // An unchanged buffer has no spare room.
	size_t whole_writes = 0;
	for (int frame = 0; frame < 400; ++frame) {
		std::vector<bool> changed(tiles, false);
		/* Three animated tiles cycle frames of different sizes; one tile grows through stages. */
		for (size_t t : {5, 17, 40}) {
			changed[t] = true;
			sizes[t] = 3 * (4 + (frame + t) % 3 * 5);
			++version[t];
		}
		size_t grower = 20 + (frame / 50);
		changed[grower] = true;
		sizes[grower] = 3 * (1 + frame % 50);
		++version[grower];
		bool whole = apply(changed);
		whole_writes += whole;
		if (!whole) {
			CHECK(writes.size() == 4);
			for (size_t t : writes) CHECK(changed[t]);
		}
		verify();
	}
	/* Grown slots settle: the cycling tiles stop forcing whole writes. */
	CHECK(whole_writes < 40);
	/* A mismatched change list writes everything into exactly fitting slots. */
	sizes.resize(tiles / 2); version.resize(tiles / 2);
	CHECK(apply(std::vector<bool>(tiles, true)));
	CHECK(slots.size == slots.used);
}

TEST_CASE("3D model slot relayout replaces previously collected partial writes")
{
	Terrain3D::TileSlots slots;
	std::vector<size_t> writes;
	REQUIRE(slots.Update({1, 1}, {}, writes));
	CHECK(writes == std::vector<size_t>{0, 1});
	/* Slot zero is queued before slot one forces a new allocation. Its upload
	 * must occur once, even though the complete buffer is now being written. */
	REQUIRE(slots.Update({1, 2}, {true, true}, writes));
	CHECK(writes == std::vector<size_t>{0, 1});
	CHECK(slots.count == std::vector<int>{1, 2});
	CHECK_FALSE(slots.Update({0, 2}, {true, false}, writes));
	CHECK(writes == std::vector<size_t>{0});
	CHECK(slots.count == std::vector<int>{0, 2});
}

TEST_CASE("3D deferred mesh changes survive repeated refreshes and eviction")
{
	struct Face {
		std::array<Terrain3D::Vec, 3> p;
		bool operator==(const Face &) const = default;
	};
	std::vector<int> authoritative(16), snapshots;
	Terrain3D::DirtyTileSet dirty;
	Terrain3D::MeshChanges pending;
	std::vector<Face> mesh, scratch;
	std::vector<Terrain3D::TileMeshSpan> spans;
	auto refresh = [&] { pending.Merge(dirty.Refresh(snapshots, 16, false, [&](size_t i) { return authoritative[i]; })); };
	auto build = [&](auto &out, size_t i) {
		for (int n = 0; n < snapshots[i]; ++n) out.push_back({{{{float(i),0,0},{float(i),1,float(n)},{float(i+1),1,0}}}});
	};
	auto prepare = [&](bool resident) {
		auto changed = pending.Take(16, !resident);
		Terrain3D::PatchTileMesh(mesh, spans, changed, scratch, build);
		std::vector<Face> reference;
		for (size_t i = 0; i < 16; ++i) build(reference, i);
		CHECK(mesh == reference);
		CHECK(pending.Empty());
	};
	refresh(); prepare(false);
	for (int frame = 0; frame < 60; ++frame) {
		size_t index = frame % 16;
		authoritative[index] = frame % 7;
		dirty.Mark(index); dirty.Mark(index);
		refresh();
		// Many offscreen refreshes coalesce; no-op refreshes cannot erase changes.
		refresh();
		if (frame % 9 == 8) prepare(true);
	}
	prepare(true);
	mesh.clear(); spans.clear();
	// Eviction requires complete regeneration even without any snapshot changes.
	prepare(false);
	// Same-sized reload cannot retain changes or geometry from the previous map.
	dirty = {}; pending = {}; snapshots.clear(); mesh.clear(); spans.clear();
	std::fill(authoritative.begin(), authoritative.end(), 1);
	refresh(); prepare(false);
}

TEST_CASE("3D mesh retention evicts oldest allocations and protects every active view")
{
	using Terrain3D::MeshEvictions;
	std::vector<Terrain3D::MeshCacheEntry> entries{{80,3,false},{60,1,false},{40,2,true},{20,0,false}};
	CHECK(MeshEvictions(entries, 200).empty());
	CHECK(MeshEvictions(entries, 120) == std::vector<size_t>{3,1});
	CHECK(MeshEvictions(entries, 0) == std::vector<size_t>{3,1,0});
	entries[0].pinned = true; // A second viewport pins a different chunk.
	CHECK(MeshEvictions(entries, 40) == std::vector<size_t>{3,1});
	entries[1].bytes = 0;
	CHECK(MeshEvictions(entries, 40) == std::vector<size_t>{3});
}

TEST_CASE("3D mesh budget keeps twice the visible chunks again, within its floor and cap")
{
	using Terrain3D::MeshBudget;
	constexpr size_t MB = 1024 * 1024;
	CHECK(MeshBudget(0) == 1536 * MB);
	CHECK(MeshBudget(505 * MB) == 1536 * MB); // 2048x512 at maximum zoom-out.
	CHECK(MeshBudget(600 * MB) == 1800 * MB);
	CHECK(MeshBudget(4096 * MB) == 2048 * MB);
}

TEST_CASE("3D dirty cells mark, test and merge the screen cells a partial render redraws")
{
	Terrain3D::DirtyCells cells(100, 70); // 4 x 3 cells; the last column and row are partial.
	CHECK(cells.Empty());
	CHECK_FALSE(cells.Overlaps(0, 0, 100, 70));
	cells.Mark(40, 40, 41, 41); // Inside cell (1, 1), with the margin still inside.
	CHECK_FALSE(cells.Empty());
	CHECK(cells.Fraction() == Approx(1.0 / 12));
	CHECK(cells.Overlaps(33, 33, 34, 34));
	CHECK(cells.Overlaps(20, 20, 31, 31)); // Within the margin of cell (1, 1).
	CHECK_FALSE(cells.Overlaps(0, 0, 20, 20));
	CHECK_FALSE(cells.Overlaps(70, 0, 99, 20));
	cells.Mark(63, 40, 64, 41); // The margin reaches cell (2, 1): one run of two cells.
	cells.Mark(98, 66, 500, 500); // Clipped to the partial corner cell.
	cells.Mark(-50, -50, -10, -10); // Off the image.
	cells.Mark(std::numeric_limits<float>::quiet_NaN(), 0, 1, 1);
	auto rects = cells.Rects();
	REQUIRE(rects.size() == 2);
	CHECK(rects[0] == std::array<int, 4>{32, 32, 64, 32});
	CHECK(rects[1] == std::array<int, 4>{96, 64, 4, 6});
	cells.Mark(-10, -10, 1000, 1000);
	CHECK(cells.Fraction() == 1.0f);
	CHECK(cells.Rects() == std::vector<std::array<int, 4>>{{0, 0, 100, 32}, {0, 32, 100, 32}, {0, 64, 100, 6}});
}
