#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, AppendEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # Configurações principais
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world_pkg = 'my_gazebo'
    ros_gz_sim_pkg = 'ros_gz_sim'

    # Paths para recursos
    world_path = os.path.join(
        get_package_share_directory(world_pkg),
        'worlds',
        'pista24B.sdf'  # Verifique se o arquivo está em formato SDF!
    )

    models_path = os.path.join(
        get_package_share_directory(world_pkg),
        'models'
    )

    # 1. Configurar variáveis de ambiente para modelos
    set_env_resources = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        models_path
    )

    # 2. Inicializar Gazebo Fortress com o mundo
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory(ros_gz_sim_pkg),
                'launch',
                'gz_sim.launch.py'
            )
        ),
        launch_arguments={
            'gz_args': f'-r -v 4 {world_path}'  # -r para rodar imediatamente, -v para verbose
        }.items()
    )

    # 3. Componentes do TurtleBot3 (serão modificados nos próximos passos)
    robot_launch_dir = os.path.join(
        get_package_share_directory('my_gazebo'),
        'launch'
    )

    robot_state_publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(robot_launch_dir, 'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    spawn_robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(robot_launch_dir, 'spawn_turtlebot3.launch.py')
        ),
        launch_arguments={
            'x_pose': LaunchConfiguration('x_pose', default='2.9'),
            'y_pose': LaunchConfiguration('y_pose', default='2.75'),
            'yaw_pose': LaunchConfiguration('yaw_pose', default='1.5697835')
        }.items()
    )

    return LaunchDescription([
        set_env_resources,
        gz_sim,
        robot_state_publisher,
        spawn_robot
    ])
