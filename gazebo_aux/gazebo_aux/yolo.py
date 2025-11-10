# yolo.py
import threading
import time
import rclpy
import os
import ros2_numpy
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.qos import ReliabilityPolicy, QoSProfile
from std_msgs.msg import String, Bool
from sensor_msgs.msg import Image
from ultralytics import YOLO
from robcomp_interfaces.msg import YoloDetector, YoloArray

class YoloDetectorNode(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        
        yolo_dir = os.path.join(get_package_share_directory('gazebo_aux'), 'gazebo_aux/', 'yolov8n.pt')
        print(yolo_dir)
        
        self.detection_model = YOLO(yolo_dir)  # Substitua pelo modelo desejado
        self.publisher_ = self.create_publisher(YoloArray, 'yolo_info', 10)
        self.detectar = False  # Flag de controle

        # Subscriber para ativar/desativar detecção
        self.create_subscription(
            Bool,
            '/poweron_yolo',
            self.detectar_callback,
            10
        )

        # Subscriber para imagem
        self.create_subscription(
            Image,
            '/camera/image_raw',
            self.yolo_callback,
            QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        )
        self.last_time = time.time()

    def detectar_callback(self, msg):
        self.detectar = msg.data
        self.get_logger().info(f"Detecção YOLO {'ATIVADA' if self.detectar else 'DESATIVADA'}")


    def yolo_callback(self, data):
        self.last_time = getattr(self, 'last_time', 0)
        if time.time() - self.last_time < 0.3:  # 3 FPS
            return
        self.last_time = time.time()
        if not self.detectar:
            return
        # Copia a imagem pra thread paralela
        threading.Thread(target=self.processa_imagem, args=(data,)).start()

    def processa_imagem(self, data):
        try:
            array = ros2_numpy.numpify(data)
            det_results = self.detection_model(array)

            yolo_list = YoloArray()
            for det_result in det_results:
                classes_int = det_result.boxes.cls.cpu().numpy().astype(int)
                names = [det_result.names[i] for i in classes_int]
                boxes = det_result.boxes.xyxy.cpu().numpy()
                scores = det_result.boxes.conf.cpu().numpy()

                for name, box, score in zip(names, boxes, scores):
                    msg = YoloDetector()
                    msg.classe = name
                    msg.boxes = [float(box[0]), float(box[1]), float(box[2]), float(box[3])]
                    msg.score = float(score)
                    yolo_list.yolos.append(msg)
            self.publisher_.publish(yolo_list)
        except Exception as e:
            self.get_logger().error(f"Erro no YOLO: {e}")


            
def main(args=None):
    rclpy.init(args=args)
    yolo_node = YoloDetectorNode()
    rclpy.spin(yolo_node)
    yolo_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
	