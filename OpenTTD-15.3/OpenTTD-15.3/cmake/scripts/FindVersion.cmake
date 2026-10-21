cmake_minimum_required(VERSION 3.17)

if(NOT REV_MAJOR)
    set(REV_MAJOR 0)
endif()
if(NOT REV_MINOR)
    set(REV_MINOR 0)
endif()

#
# Finds the current version of the current folder.
#

find_package(Git QUIET)
# This fork's source can live below the workspace Git root. An exported
# source archive's .ottdrev must still win over an unrelated enclosing repo.
set(IN_GIT_WORKTREE FALSE)
if(GIT_FOUND AND (EXISTS "${CMAKE_SOURCE_DIR}/.git" OR NOT EXISTS "${CMAKE_SOURCE_DIR}/.ottdrev"))
    execute_process(COMMAND ${GIT_EXECUTABLE} rev-parse --is-inside-work-tree
                    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                    OUTPUT_VARIABLE IN_GIT_WORKTREE
                    OUTPUT_STRIP_TRAILING_WHITESPACE
                    ERROR_QUIET
    )
endif()
# ${CMAKE_SOURCE_DIR}/.git may be a directory or a regular file
if(IN_GIT_WORKTREE STREQUAL "true")
    # Make sure LC_ALL is set to something desirable
    set(SAVED_LC_ALL "$ENV{LC_ALL}")
    set(ENV{LC_ALL} C)

    # Assume the dir is not modified
    set(REV_MODIFIED 0)

    # Include new source files as well, without writing the workspace index.
    execute_process(COMMAND ${GIT_EXECUTABLE} --no-optional-locks status --porcelain --untracked-files=normal
                    OUTPUT_VARIABLE IS_MODIFIED
                    OUTPUT_STRIP_TRAILING_WHITESPACE
                    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    )
    if(NOT IS_MODIFIED STREQUAL "")
        set(REV_MODIFIED 2)
    endif()

    # Get last commit hash
    execute_process(COMMAND ${GIT_EXECUTABLE} rev-parse --verify HEAD
                    OUTPUT_VARIABLE FULLHASH
                    OUTPUT_STRIP_TRAILING_WHITESPACE
                    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                    ERROR_QUIET
    )
    set(REV_HASH "${FULLHASH}")

    string(SUBSTRING "${FULLHASH}" 0 10 SHORTHASH)

    # Get the last commit date
    set(ENV{TZ} "UTC0")
    execute_process(COMMAND ${GIT_EXECUTABLE} show -s --date=iso-local --pretty=format:%cd HEAD
                    OUTPUT_VARIABLE COMMITDATE
                    OUTPUT_STRIP_TRAILING_WHITESPACE
                    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    )
    string(REGEX REPLACE "([0-9]+)-([0-9]+)-([0-9]+).*" "\\1\\2\\3" COMMITDATE "${COMMITDATE}")
    set(REV_ISODATE "${COMMITDATE}")

    # Get the branch
    execute_process(COMMAND ${GIT_EXECUTABLE} symbolic-ref -q HEAD
                    OUTPUT_VARIABLE BRANCH
                    OUTPUT_STRIP_TRAILING_WHITESPACE
                    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                    ERROR_QUIET
    )
    string(REGEX REPLACE ".*/" "" BRANCH "${BRANCH}")

    # Get the tag
    execute_process(COMMAND ${GIT_EXECUTABLE} name-rev --name-only --tags --no-undefined HEAD
                    OUTPUT_VARIABLE TAG
                    OUTPUT_STRIP_TRAILING_WHITESPACE
                    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                    ERROR_QUIET
    )
    string(REGEX REPLACE "\^0$" "" TAG "${TAG}")

    if(REV_MODIFIED EQUAL 0)
        set(HASHPREFIX "-g")
    elseif(REV_MODIFIED EQUAL 2)
        set(HASHPREFIX "-m")
    else()
        set(HASHPREFIX "-u")
    endif()

    # Set the version string
    if(NOT TAG STREQUAL "")
        set(REV_VERSION "${TAG}")
        set(REV_ISTAG 1)

        string(REGEX REPLACE "^[0-9.]+$" "" STABLETAG "${TAG}")
        if(STABLETAG STREQUAL "")
            set(REV_ISSTABLETAG 1)
        else()
            set(REV_ISSTABLETAG 0)
        endif()
    else()
        set(REV_VERSION "${REV_ISODATE}-${BRANCH}${HASHPREFIX}${SHORTHASH}")
        set(REV_ISTAG 0)
        set(REV_ISSTABLETAG 0)
    endif()

    # Restore LC_ALL
    set(ENV{LC_ALL} "${SAVED_LC_ALL}")
elseif(EXISTS "${CMAKE_SOURCE_DIR}/.ottdrev")
    file(READ "${CMAKE_SOURCE_DIR}/.ottdrev" OTTDREV)
    string(REPLACE "\n" "" OTTDREV "${OTTDREV}")
    string(REPLACE "\t" ";" OTTDREV "${OTTDREV}")
    list(GET OTTDREV 0 REV_VERSION)
    list(GET OTTDREV 1 REV_ISODATE)
    list(GET OTTDREV 2 REV_MODIFIED)
    list(GET OTTDREV 3 REV_HASH)
    list(GET OTTDREV 4 REV_ISTAG)
    list(GET OTTDREV 5 REV_ISSTABLETAG)
else()
    message(WARNING "No version detected; this build will NOT be network compatible")
    set(REV_VERSION "norev0000")
    set(REV_ISODATE "19700101")
    set(REV_MODIFIED 1)
    set(REV_HASH "unknown")
    set(REV_ISTAG 0)
    set(REV_ISSTABLETAG 0)
endif()

if(DEFINED OPENTTD_3D_VERSION AND NOT OPENTTD_3D_VERSION STREQUAL "")
    if(NOT OPENTTD_3D_VERSION MATCHES "^[A-Za-z0-9][A-Za-z0-9._-]*$" OR REV_HASH STREQUAL "unknown")
        message(FATAL_ERROR "A fork version needs a simple label and Git or .ottdrev revision metadata")
    endif()
    string(SUBSTRING "${REV_HASH}" 0 10 SHORTHASH)
    if(REV_MODIFIED EQUAL 0)
        set(FORK_HASH_PREFIX "g")
    elseif(REV_MODIFIED EQUAL 2)
        set(FORK_HASH_PREFIX "m")
    else()
        set(FORK_HASH_PREFIX "u")
    endif()
    set(REV_VERSION "${OPENTTD_3D_VERSION}-${FORK_HASH_PREFIX}${SHORTHASH}")
    string(LENGTH "${REV_VERSION}" FORK_VERSION_LENGTH)
    if(FORK_VERSION_LENGTH GREATER 32)
        message(FATAL_ERROR "Fork version exceeds the 32-character network revision limit; shorten the label")
    endif()
    set(REV_ISTAG 0)
    set(REV_ISSTABLETAG 0)
endif()

# Record archive metadata alongside the build, without modifying the checkout.
if(DEFINED FIND_VERSION_BINARY_DIR)
    file(WRITE "${FIND_VERSION_BINARY_DIR}/.ottdrev" "${REV_VERSION}\t${REV_ISODATE}\t${REV_MODIFIED}\t${REV_HASH}\t${REV_ISTAG}\t${REV_ISSTABLETAG}\n")
endif()

# Extract REV_YEAR and REV_DATE from REV_ISODATE
string(SUBSTRING "${REV_ISODATE}" 0 4 REV_YEAR)
string(SUBSTRING "${REV_ISODATE}" 4 4 REV_DATE)
# Drop leading 0 in REV_DATE if any
string(REGEX REPLACE "^0?([0-9]+)" "\\1" REV_DATE "${REV_DATE}")

message(STATUS "Version string: ${REV_VERSION}")

if(GENERATE_OTTDREV)
    message(STATUS "Generating .ottdrev")
    file(WRITE ${CMAKE_SOURCE_DIR}/.ottdrev "${REV_VERSION}\t${REV_ISODATE}\t${REV_MODIFIED}\t${REV_HASH}\t${REV_ISTAG}\t${REV_ISSTABLETAG}\n")
else()
    if(REV_ISSTABLETAG AND NOT (REV_VERSION STREQUAL "${REV_MAJOR}.${REV_MINOR}"))
        message(FATAL_ERROR "Tag (${REV_VERSION}) doesn't match internal version (${REV_MAJOR}.${REV_MINOR})")
    endif()
    message(STATUS "Generating rev.cpp")
    configure_file("${CMAKE_SOURCE_DIR}/src/rev.cpp.in"
            "${FIND_VERSION_BINARY_DIR}/rev.cpp")

    if(WINDOWS)
        message(STATUS "Generating ottdres.rc")
        configure_file("${CMAKE_SOURCE_DIR}/src/os/windows/ottdres.rc.in"
                "${FIND_VERSION_BINARY_DIR}/ottdres.rc")
    endif()

    message(STATUS "Generating CPackProperties.cmake")
    configure_file("${CMAKE_SOURCE_DIR}/CPackProperties.cmake.in"
            "${CPACK_BINARY_DIR}/CPackProperties.cmake" @ONLY)

    message(STATUS "Generating Doxyfile")
    configure_file("${CMAKE_SOURCE_DIR}/Doxyfile.in"
            "${CPACK_BINARY_DIR}/Doxyfile")

    message(STATUS "Generating Doxyfile_AI")
    configure_file("${CMAKE_SOURCE_DIR}/src/script/api/Doxyfile_AI.in"
            "${CPACK_BINARY_DIR}/Doxyfile_AI")

    message(STATUS "Generating Doxyfile_GS")
    configure_file("${CMAKE_SOURCE_DIR}/src/script/api/Doxyfile_GS.in"
            "${CPACK_BINARY_DIR}/Doxyfile_GS")
endif()
