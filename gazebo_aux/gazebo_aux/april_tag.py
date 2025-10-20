import rclpy
from rclpy.node import Node
from robcomp_interfaces.msg import Taginfo, TaginfoArray
from geometry_msgs.msg import Point
from apriltag_msgs.msg import AprilTagDetectionArray
import numpy as np
import cv2

class TagPublisher(Node):
    def __init__(self):
        super().__init__('tag_publisher')
        self.publisher_ = self.create_publisher(TaginfoArray, 'tag_list', 10)
        self.subscription = self.create_subscription(
            AprilTagDetectionArray,
            '/detections',
            self.listener_callback,
            10)
        self.camera_matrix = np.array([[600, 0, 640],
                                       [0, 600, 480],
                                       [0, 0, 1]], dtype=float)
        self.dist_coeffs = np.zeros((5, 1))  # Supondo sem distorção
        self.smallTag = 0.045  # Tamanho do lado do marcador pequeno em metros
        self.largeTag = 0.07  # Tamanho do lado do marcador grande em metros
        self.LastSmallTag = 99 # Último tamanho do marcador pequeno
    
    def listener_callback(self, msg):
        tag_list = TaginfoArray()
        for detection in msg.detections:
            tag_id = detection.id
            center = Point()
            center.x = detection.centre.x
            center.y = detection.centre.y
            center.z = 0.0

            if tag_id <= self.LastSmallTag: self.tag_size = self.smallTag
            else: self.tag_size = self.largeTag
            half_size = self.tag_size / 2.0
            self.object_points = np.array([
                [-half_size,  half_size, 0],
                [ half_size,  half_size, 0],
                [ half_size, -half_size, 0],
                [-half_size, -half_size, 0]
            ])

            # Extrai os cantos 2D do marcador
            image_points = np.array([
                [detection.corners[0].x, detection.corners[0].y],
                [detection.corners[1].x, detection.corners[1].y],
                [detection.corners[2].x, detection.corners[2].y],
                [detection.corners[3].x, detection.corners[3].y]
            ], dtype=float)
            # Calcula pose usando solvePnP
            success, rvec, tvec = cv2.solvePnP(
                self.object_points,
                image_points,
                self.camera_matrix,
                self.dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if success:
                distance = np.linalg.norm(tvec)
            else:
                distance = float('nan')


            tag_info = Taginfo()
            tag_info.id = tag_id
            tag_info.center = center
            tag_info.distance = distance
            tag_list.tags.append(tag_info)
        self.publisher_.publish(tag_list)

def main(args=None):
    rclpy.init(args=args)
    node = TagPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
