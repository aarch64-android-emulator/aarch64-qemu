# Copyright 2018 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# This invokes the toolchain generator
# HOST
#   The host to use
# PARAM1, PARAM2
#   Parameters to pass on to the gen-android-sdk-toolchain.sh script.
#
# Sets STD_OUT
#   The output produced by the script
function(toolchain_cmd HOST PARAM1 PARAM2)
    get_filename_component(GEN_SDK "${CMAKE_CURRENT_LIST_FILE}/../../../scripts/gen-android-sdk-toolchain.sh" ABSOLUTE)
    execute_process(COMMAND ${GEN_SDK} "--host=${HOST}" "${PARAM1}" "${PARAM2}" "--verbosity=0"
        RESULT_VARIABLE GEN_SDK_RES
        OUTPUT_VARIABLE STD_OUT
        ERROR_VARIABLE STD_ERR)
    if(NOT "${GEN_SDK_RES}" STREQUAL "0")
        message(FATAL_ERROR "Unable to retrieve sdk info from ${GEN_SDK} : ${STD_OUT}, ${STD_ERR}")
    endif()

    # Clean up and make visibile
    string(REPLACE "\n" "" STD_OUT "${STD_OUT}")
    set(STD_OUT ${STD_OUT} PARENT_SCOPE)
endfunction ()

# Generates the toolchain for the given host.
# The toolchain is generated by calling the gen-android-sdk script
#
# It will set the all the necesary CMAKE compiler flags to use the
# android toolchain for the given host.
#
# TARGET_OS:
#   The target environment for which we are creating the toolchain
#
# Returns:
#   The variable ANDROID_SYSROOT will be set to point to the sysroot for the
#   target os.
#   The variablke ANDROID_COMPILER_PREFIX will point to the prefix for
#     gcc, g++, ar, ld etc..
function(toolchain_generate_internal TARGET_OS)
    set(TOOLCHAIN "${PROJECT_BINARY_DIR}/toolchain")

    # First we generate the toolchain.
    if (NOT EXISTS ${TOOLCHAIN})
        message(STATUS "Creating the toolchain in ${TOOLCHAIN} with aosp: ${AOSP}")
        toolchain_cmd("${TARGET_OS}" "--aosp-dir=${AOSP}" "${TOOLCHAIN}")
    endif ()

    # Let's find the bin-prefix
    toolchain_cmd("${TARGET_OS}" "--print=binprefix" "unused")
    set(ANDROID_COMPILER_PREFIX "${TOOLCHAIN}/${STD_OUT}" PARENT_SCOPE)

    # And define all the compilers..
    toolchain_cmd("${TARGET_OS}" "--print=sysroot" "unused")
    set(ANDROID_SYSROOT "${STD_OUT}" PARENT_SCOPE)
endfunction ()

# Gets the given key from the enviroment. This your usual shell environment
# and is globally visuable during cmake generation. This used by the toolchain
# generator to work around some caching issues.
function(get_env_cache KEY)
    set(${KEY} $ENV{ENV_CACHE_${KEY}} PARENT_SCOPE)
endfunction()

# Sets the given key in the environment to the given value.
function(set_env_cache KEY VAL)
    set(ENV{ENV_CACHE_${KEY}} "${VAL}")
    set(${KEY} "${VAL}" PARENT_SCOPE)
endfunction()

function(toolchain_generate TARGET_OS)
    # This is a hack to workaround the fact that cmake will keep including
    # the toolchain defintion over and over, and it will wipe out all the settings.
    # so we will just store them in the environment, which gets blown away on exit
    # anyway..
    get_env_cache(COMPILER_PREFIX)
    get_env_cache(ANDROID_SYSROOT)
    if ("${COMPILER_PREFIX}" STREQUAL "")
        toolchain_generate_internal(${TARGET_OS})
        set_env_cache(COMPILER_PREFIX "${ANDROID_COMPILER_PREFIX}")
        set_env_cache(ANDROID_SYSROOT "${ANDROID_SYSROOT}")
    endif ()

    set(CMAKE_RC_COMPILER ${COMPILER_PREFIX}windres PARENT_SCOPE)
    set(CMAKE_C_COMPILER ${COMPILER_PREFIX}gcc PARENT_SCOPE)
    set(CMAKE_CXX_COMPILER ${COMPILER_PREFIX}g++ PARENT_SCOPE)
    # We will use system bintools
    # set(CMAKE_AR ${COMPILER_PREFIX}ar PARENT_SCOPE)
    set(CMAKE_RANLIB ${COMPILER_PREFIX}ranlib PARENT_SCOPE)
    set(CMAKE_OBJCOPY ${COMPILER_PREFIX}objcopy PARENT_SCOPE)
    set(ANDROID_SYSROOT ${ANDROID_SYSROOT} PARENT_SCOPE)
endfunction()

get_filename_component(ANDROID_QEMU2_TOP_DIR "${CMAKE_CURRENT_LIST_FILE}/../../../.." ABSOLUTE)
