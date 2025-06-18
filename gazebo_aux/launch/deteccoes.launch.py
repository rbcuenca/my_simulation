from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='apriltag_ros',
            executable='apriltag_node',
            name='apriltag_node',
            remappings=[
                ('image_rect', '/camera/image_raw'),
                ('camera_info', '/camera/camera_info'),
            ],
            parameters=[{'tag_family': 'tag36h11'}],
        ),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=['/camera/image_raw@sensor_msgs/msg/Image@gz.msgs.Image'],
        ),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=['/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo'],
        ),
        Node(
            package='gazebo_aux',
            executable='april_tag',
            name='april_tag',
        ),
        Node(
            package='gazebo_aux',
            executable='yolo',
            name='yolo_detector',
        )
    ])
