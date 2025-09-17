cmake_minimum_required(VERSION 3.8)
project(robcomp_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Encontrar dependências
find_package(rclcpp REQUIRED)
find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(action_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Listar todos os arquivos de mensagens e ações
set(msg_files
  "msg/Conversation.msg"
  "msg/GameStatus.msg"
  "msg/HandlerAF25a.msg"
  "msg/Taginfo.msg"
  "msg/TaginfoArray.msg"
  "msg/YoloDetector.msg"
  "msg/YoloArray.msg"
  "msg/PubSubAPS.msg"
)

set(action_files
  "action/SimpleStart.action"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  ${action_files}
  DEPENDENCIES geometry_msgs std_msgs action_msgs
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_cpplint_FOUND TRUE)
  set(ament_cmake_cppcheck_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()