/*
 * This file is part of OpenTTD.
 * OpenTTD is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, version 2.
 * OpenTTD is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with OpenTTD. If not, see <https://www.gnu.org/licenses/old-licenses/gpl-2.0>.
 */

/** @file film_cmd.cpp Presentation-only trailer direction: timed cues and eased camera moves of the main view. */

#include "stdafx.h"
#include "console_func.h"
#include "gfx_func.h"
#include "landscape.h"
#include "map_func.h"
#include "settings_type.h"
#include "vehicle_base.h"
#include "viewport_func.h"
#include "window_func.h"
#include "window_gui.h"
#include "video/proof3d.h"
#include "video/video_driver.hpp"
#include <charconv>
#include <cmath>
#include <optional>

#include "safeguards.h"

bool _film_hide_cursor = false;

namespace {

using FilmClock = std::chrono::steady_clock;

/** A console command waiting for its moment on the trailer clock. */
struct FilmCue {
	double at;
	std::string command;
};

/** One eased move from a start value to an end value over a span of the trailer clock. */
struct FilmTween {
	double start = 0, seconds = 0;
	bool active = false;
	bool linear = false;

	/** Progress from 0 to 1, eased in and out unless linear. */
	double Progress(double now) const
	{
		double t = this->seconds <= 0 ? 1 : std::clamp((now - this->start) / this->seconds, 0.0, 1.0);
		return this->linear ? t : t * t * (3 - 2 * t);
	}
	bool Done(double now) const { return now >= this->start + this->seconds; }
};

static std::optional<FilmClock::time_point> _film_epoch;
static std::vector<FilmCue> _film_cues;
static bool _film_ticking = false;
/** While a cue runs, its scheduled time: moves it starts are timed from there, so they end on the beat of later cues. */
static std::optional<double> _film_cue_time;

static struct { FilmTween tween; float from_yaw, from_tilt, to_yaw, to_tilt; } _film_camera;
static struct { FilmTween tween; float from_x, from_y, to_x, to_y; } _film_pan;
/** Zooms glide in powers of two of magnification; the real zoom level changes where it hides the jump. */
static struct { FilmTween tween; float from, to; int final_zoom; } _film_zoom;
static bool _film_ui_hidden = false;
static bool _film_saved_hints = true;

static double FilmNow()
{
	if (!_film_epoch.has_value()) _film_epoch = FilmClock::now();
	return std::chrono::duration<double>(FilmClock::now() - *_film_epoch).count();
}

static bool ParseNumber(std::string_view text, double &value)
{
	auto result = std::from_chars(text.data(), text.data() + text.size(), value);
	return result.ec == std::errc{} && result.ptr == text.data() + text.size();
}

static void SetMainZoom(int level)
{
	Window *w = GetMainWindow();
	while (static_cast<int>(w->viewport->zoom) > level && DoZoomInOutWindow(ZOOM_IN, w)) {}
	while (static_cast<int>(w->viewport->zoom) < level && DoZoomInOutWindow(ZOOM_OUT, w)) {}
}

/** The world point at the centre of the main view. */
static Point MainViewCentre()
{
	const Viewport &vp = *GetMainWindow()->viewport;
	return TranslateXYToTileCoord(vp, vp.left + vp.width / 2, vp.top + vp.height / 2);
}

static void CentreMainView(float x, float y)
{
	int ix = std::clamp(static_cast<int>(x), 0, static_cast<int>(Map::MaxX() * TILE_SIZE) - 1);
	int iy = std::clamp(static_cast<int>(y), 0, static_cast<int>(Map::MaxY() * TILE_SIZE) - 1);
	ScrollWindowTo(ix, iy, GetSlopePixelZ(ix, iy), GetMainWindow(), true);
}

/** Advance every move and run the cues that are due; once per drawn frame while anything is pending. */
static void FilmTick()
{
	_film_ticking = false;
	Window *main = GetMainWindow();
	if (main == nullptr || main->viewport == nullptr) {
		_film_cues.clear();
		return;
	}
	double now = FilmNow();

	if (_film_camera.tween.active) {
		auto &c = _film_camera;
		float t = static_cast<float>(c.tween.Progress(now));
		float yaw = c.from_yaw + (c.to_yaw - c.from_yaw) * t;
		if (c.tween.Done(now)) {
			yaw = std::fmod(c.to_yaw, 360.0f);
			if (yaw < 0) yaw += 360;
			c.tween.active = false;
		}
		PlaceTerrain3DCamera(yaw, c.from_tilt + (c.to_tilt - c.from_tilt) * t);
	}
	if (_film_pan.tween.active) {
		auto &p = _film_pan;
		float t = static_cast<float>(p.tween.Progress(now));
		CentreMainView(p.from_x + (p.to_x - p.from_x) * t, p.from_y + (p.to_y - p.from_y) * t);
		if (p.tween.Done(now)) p.tween.active = false;
	}
	if (_film_zoom.tween.active) {
		auto &z = _film_zoom;
		float t = static_cast<float>(z.tween.Progress(now));
		SetTerrain3DMagnify(std::exp2(z.from + (z.to - z.from) * t));
		if (z.tween.Done(now)) {
			/* Changing the zoom level keeps the view centre, so the swap back to plain zoom is seamless. */
			z.tween.active = false;
			SetTerrain3DMagnify(1);
			SetMainZoom(z.final_zoom);
		}
	}
	if (_film_camera.tween.active || _film_pan.tween.active || _film_zoom.tween.active) main->SetDirty();

	/* Cues may add further cues and moves; run the due ones in order of their time. */
	std::stable_sort(_film_cues.begin(), _film_cues.end(), [](const FilmCue &a, const FilmCue &b) { return a.at < b.at; });
	while (!_film_cues.empty() && _film_cues.front().at <= now) {
		std::string command = std::move(_film_cues.front().command);
		_film_cue_time = _film_cues.front().at;
		_film_cues.erase(_film_cues.begin());
		IConsoleCmdExec(command);
		_film_cue_time.reset();
	}

	if (!_film_cues.empty() || _film_camera.tween.active || _film_pan.tween.active || _film_zoom.tween.active) {
		_film_ticking = true;
		VideoDriver::GetInstance()->QueueOnMainThread(FilmTick);
	}
}

static void EnsureFilmTick()
{
	if (_film_ticking) return;
	_film_ticking = true;
	VideoDriver::GetInstance()->QueueOnMainThread(FilmTick);
}

/** A primary vehicle by id, or the first of a type: train, road, ship or aircraft. */
static const Vehicle *FindFilmVehicle(std::string_view target)
{
	static const std::array<std::string_view, 4> types{"train", "road", "ship", "aircraft"};
	auto type = std::find(types.begin(), types.end(), target);
	if (type != types.end()) {
		for (const Vehicle *v : Vehicle::Iterate()) {
			if (v->IsPrimaryVehicle() && v->type == static_cast<VehicleType>(type - types.begin())) return v;
		}
		return nullptr;
	}
	uint32_t id = 0;
	if (std::from_chars(target.data(), target.data() + target.size(), id).ec != std::errc{}) return nullptr;
	const Vehicle *v = Vehicle::GetIfValid(VehicleID(id));
	return v != nullptr && v->IsPrimaryVehicle() ? v : nullptr;
}

static void ShowFilmHelp()
{
	IConsolePrint(CC_HELP, "Trailer direction of the main view, presentation only. Times are seconds on the trailer clock.");
	IConsolePrint(CC_HELP, "  film start                      restart the clock and drop pending cues and moves");
	IConsolePrint(CC_HELP, "  film at <seconds> <command>     run a console command at that time");
	IConsolePrint(CC_HELP, "  film zoom <level> <seconds>     glide to a zoom level (3D; jumps in classic)");
	IConsolePrint(CC_HELP, "  film camera <yaw> <tilt> <seconds>   glide to a 3D camera angle the short way round");
	IConsolePrint(CC_HELP, "  film orbit <+yaw> <+tilt> <seconds>  turn the 3D camera at a steady speed");
	IConsolePrint(CC_HELP, "  film pan <x> <y> <seconds>      glide the view centre to a tile");
	IConsolePrint(CC_HELP, "  film ride <vehicle id|train|road|ship|aircraft> cab|chase   ride in the main view");
	IConsolePrint(CC_HELP, "  film follow <vehicle id|train|road|ship|aircraft>   keep the main view centred on a vehicle");
	IConsolePrint(CC_HELP, "  film ride off | film follow off");
	IConsolePrint(CC_HELP, "  film ui off|on                  hide or show toolbars, windows, camera hints and the cursor");
}

} // namespace

bool ConFilm(std::span<std::string_view> argv)
{
	if (argv.size() < 2) {
		ShowFilmHelp();
		return true;
	}
	Window *main = GetMainWindow();
	if (main == nullptr || main->viewport == nullptr) return false;
	ViewportData &vp = *main->viewport;
	std::string_view action = argv[1];
	double now = _film_cue_time.value_or(FilmNow());

	if (action == "start" && argv.size() == 2) {
		_film_epoch = FilmClock::now();
		_film_cues.clear();
		_film_camera.tween.active = _film_pan.tween.active = false;
		if (_film_zoom.tween.active) {
			_film_zoom.tween.active = false;
			SetTerrain3DMagnify(1);
			SetMainZoom(_film_zoom.final_zoom);
		}
		return true;
	}
	if (action == "at" && argv.size() >= 4) {
		double at = 0;
		if (!ParseNumber(argv[2], at)) return false;
		std::string command;
		for (std::string_view arg : argv.subspan(3)) command += fmt::format("{}{}", command.empty() ? "" : " ", arg);
		_film_cues.push_back({at, std::move(command)});
		EnsureFilmTick();
		return true;
	}
	if (action == "zoom" && argv.size() == 4) {
		double level = 0, seconds = 0;
		if (!ParseNumber(argv[2], level) || !ParseNumber(argv[3], seconds)) return false;
		int target = std::clamp(static_cast<int>(level), static_cast<int>(_settings_client.gui.zoom_min), static_cast<int>(_settings_client.gui.zoom_max));
		/* Finish a zoom still under way, so the next one starts from a real zoom level. */
		if (_film_zoom.tween.active) {
			_film_zoom.tween.active = false;
			SetTerrain3DMagnify(1);
			SetMainZoom(_film_zoom.final_zoom);
		}
		int from = static_cast<int>(vp.zoom);
		if (!IsProof3DEnabled() || seconds <= 0 || target == from) {
			SetMainZoom(target);
			return true;
		}
		/* Draw at the wider of the two levels throughout, magnified, so zooming in never runs past the drawn area. */
		if (target > from) {
			SetMainZoom(target);
			_film_zoom.from = static_cast<float>(target - from);
			_film_zoom.to = 0;
		} else {
			_film_zoom.from = 0;
			_film_zoom.to = static_cast<float>(from - target);
		}
		SetTerrain3DMagnify(std::exp2(_film_zoom.from));
		_film_zoom.final_zoom = target;
		_film_zoom.tween = {now, seconds, true, false};
		EnsureFilmTick();
		return true;
	}
	if ((action == "camera" || action == "orbit") && argv.size() == 5) {
		double yaw = 0, tilt = 0, seconds = 0;
		if (!ParseNumber(argv[2], yaw) || !ParseNumber(argv[3], tilt) || !ParseNumber(argv[4], seconds)) return false;
		if (!IsProof3DEnabled()) return true;
		auto [cur_yaw, cur_tilt] = GetTerrain3DCamera();
		auto &c = _film_camera;
		c.from_yaw = cur_yaw;
		c.from_tilt = cur_tilt;
		if (action == "camera") {
			c.to_yaw = cur_yaw + std::remainder(static_cast<float>(yaw) - cur_yaw, 360.0f);
			c.to_tilt = static_cast<float>(tilt);
		} else {
			c.to_yaw = cur_yaw + static_cast<float>(yaw);
			c.to_tilt = cur_tilt + static_cast<float>(tilt);
		}
		c.to_tilt = std::clamp(c.to_tilt, 40.0f, 180.0f);
		c.tween = {now, seconds, true, action == "orbit"};
		EnsureFilmTick();
		return true;
	}
	if (action == "pan" && argv.size() == 5) {
		double x = 0, y = 0, seconds = 0;
		if (!ParseNumber(argv[2], x) || !ParseNumber(argv[3], y) || !ParseNumber(argv[4], seconds)) return false;
		vp.follow_vehicle = VehicleID::Invalid();
		Point centre = MainViewCentre();
		auto &p = _film_pan;
		p.to_x = static_cast<float>(x * TILE_SIZE + TILE_SIZE / 2);
		p.to_y = static_cast<float>(y * TILE_SIZE + TILE_SIZE / 2);
		p.from_x = centre.x >= 0 ? static_cast<float>(centre.x) : p.to_x;
		p.from_y = centre.y >= 0 ? static_cast<float>(centre.y) : p.to_y;
		p.tween = {now, seconds, true, false};
		EnsureFilmTick();
		return true;
	}
	if (action == "ride" && argv.size() == 3 && argv[2] == "off") {
		vp.camera_3d = ViewportCamera3D::Normal;
		vp.camera_vehicle = VehicleID::Invalid();
		vp.camera_follow_set = false;
		main->SetDirty();
		return true;
	}
	if (action == "ride" && argv.size() == 4 && (argv[3] == "cab" || argv[3] == "chase")) {
		const Vehicle *v = FindFilmVehicle(argv[2]);
		if (v == nullptr) { IConsolePrint(CC_ERROR, "No primary vehicle {}.", argv[2]); return true; }
		if (!IsProof3DEnabled()) return true;
		vp.follow_vehicle = VehicleID::Invalid();
		vp.camera_vehicle = v->index;
		vp.camera_3d = argv[3] == "cab" ? ViewportCamera3D::Cab : ViewportCamera3D::Chase;
		vp.camera_follow_set = false;
		main->SetDirty();
		return true;
	}
	if (action == "follow" && argv.size() == 3) {
		if (argv[2] == "off") {
			vp.follow_vehicle = VehicleID::Invalid();
			return true;
		}
		const Vehicle *v = FindFilmVehicle(argv[2]);
		if (v == nullptr) { IConsolePrint(CC_ERROR, "No primary vehicle {}.", argv[2]); return true; }
		_film_pan.tween.active = false;
		vp.follow_vehicle = v->index;
		return true;
	}
	if (action == "ui" && argv.size() == 3 && (argv[2] == "on" || argv[2] == "off")) {
		bool hide = argv[2] == "off";
		if (hide == _film_ui_hidden) return true;
		_film_ui_hidden = hide;
		if (hide) {
			_film_saved_hints = _settings_client.gui.renderer_3d_camera_hints;
			_settings_client.gui.renderer_3d_camera_hints = false;
			CloseAllNonVitalWindows();
			CloseWindowById(WC_MAIN_TOOLBAR, 0);
			CloseWindowById(WC_STATUS_BAR, 0);
		} else {
			_settings_client.gui.renderer_3d_camera_hints = _film_saved_hints;
			ShowVitalWindows();
		}
		_film_hide_cursor = hide;
		MarkWholeScreenDirty();
		return true;
	}
	ShowFilmHelp();
	return true;
}
