cmake_minimum_required(VERSION 3.15)
project(techdebt_cli LANGUAGES NONE)

find_package(Python3 COMPONENTS Interpreter REQUIRED)

set(TECHDEBT_SCAN_DIR "${CMAKE_SOURCE_DIR}" CACHE PATH "Directory to scan for tech debt")

add_custom_target(techdebt
    COMMAND ${CMAKE_COMMAND} -E env PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}/src
            ${Python3_EXECUTABLE} -m techdebt_cli scan ${TECHDEBT_SCAN_DIR} --markdown --json
    WORKING_DIRECTORY ${TECHDEBT_SCAN_DIR}
    COMMENT "Running techdebt-cli on ${TECHDEBT_SCAN_DIR}"
)
