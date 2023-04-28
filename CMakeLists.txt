# CMakeList.txt : Top-level CMake project file, do global configuration
# and include sub-projects here.
#
cmake_minimum_required (VERSION 3.18)

project ("TheSimulator" VERSION 2.0.0 LANGUAGES CXX)

# C++ standard
set (CMAKE_CXX_STANDARD_REQUIRED ON)
set (CMAKE_CXX_STANDARD 17)

#set(Python_FIND_VERSION 3.10)

#set (PYTHON_EXECUTABLE "~/anaconda3/envs/bin/python3.10")
#set(PYTHON_LIBRARY "~/anaconda3/envs/lib/python3.10")
#set (CMAKE_LIBRARY_PATH "~anaconda3/envs/Simulation/lib")
#set (CMAKE_INCLUDE_PATH "~anaconda3/envs/Simulation/include")
#
#set (CMAKE_PREFIX_PATH "~anaconda3/envs/Simulation/")

#set(PYTHON_INCLUDE_PATH "~/anaconda3/envs/Simulation/")

#find_package(Python COMPONENTS Interpreter Development)

# Include sub-projects.

add_subdirectory(pybind11)
add_subdirectory ("TheSimulator")

set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

target_link_libraries("TheSimulator" PRIVATE pybind11::embed Threads::Threads)

# To Check if we need filesystem
include(CheckCXXSymbolExists)
CHECK_CXX_SYMBOL_EXISTS(std::filesystem::path::preferred_separator filesystem cxx17fs)

if(NOT cxx17fs)
    target_link_libraries("TheSimulator" PRIVATE stdc++fs)
endif()