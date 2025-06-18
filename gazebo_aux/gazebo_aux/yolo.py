import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from sensor_msgs.msg import Image
from rclpy.qos import ReliabilityPolicy, QoSProfile
import ros2_numpy
from ultralytics import YOLO
from robcomp_interfaces.msg import YoloDetector, YoloArray

class YoloDetectorNode(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        self.detection_model = YOLO("yolov8n.pt")  # Substitua pelo modelo desejado
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

    def detectar_callback(self, msg):
        self.detectar = msg.data
        self.get_logger().info(f"Detecção YOLO {'ATIVADA' if self.detectar else 'DESATIVADA'}")

    def yolo_callback(self, data):
        yolo_list = YoloArray()
        if not self.detectar:
            return  # Não processa se flag estiver False
        array = ros2_numpy.numpify(data)
        det_results = self.detection_model(array)
        if self.publisher_.get_subscription_count() > 0:
            for det_result in det_results:
                classes_int = det_result.boxes.cls.cpu().numpy().astype(int)
                names = [det_result.names[i] for i in classes_int]
                boxes = det_result.boxes.xyxy.cpu().numpy()  # shape: (N, 4)
                scores = det_result.boxes.conf.cpu().numpy()  # shape: (N,)
                for name, box, score in zip(names, boxes, scores):
                    msg = YoloDetector()
                    msg.classe = name
                    msg.boxes = [float(box[0]), float(box[1]), float(box[2]), float(box[3])]
                    msg.score = float(score)
                    yolo_list.yolos.append(msg)
                    # self.get_logger().info(
                    #         f"Publicado: {msg.classe}, boxes: {msg.boxes}, score: {msg.score:.2f}"
                    #     )
        self.publisher_.publish(yolo_list)

            
def main(args=None):
    rclpy.init(args=args)
    yolo_node = YoloDetectorNode()
    rclpy.spin(yolo_node)
    yolo_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
