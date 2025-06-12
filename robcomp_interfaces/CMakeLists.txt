cmake_minimum_required(VERSION 3.8)
project(robcomp_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Encontrar dependências
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(action_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Listar todos os arquivos de mensagens e ações
set(msg_files
  "msg/Detection.msg"
  "msg/DetectionArray.msg"
  "msg/Conversation.msg"
  "msg/GameStatus.msg"
  "msg/HandlerAF25a.msg"
  "msg/AprilTagInsper.msg"
  "msg/AprilTagInsperArray.msg"
  "msg/YoloDetector.msg"
  "msg/YoloDetectorArray.msg"
)

set(action_files
  "action/GoToPoint.action"
  "action/SimpleStart.action"
)

# Combinar todas as mensagens e ações em uma única chamada
rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  ${action_files}
  DEPENDENCIES geometry_msgs
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # as linhas seguintes pulam verificações de linting; remova-as se necessário
  set(ament_cmake_cpplint_FOUND TRUE)
  set(ament_cmake_cppcheck_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
