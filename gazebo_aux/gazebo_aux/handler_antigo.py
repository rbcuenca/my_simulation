import rclpy
from rclpy.node import Node
from rclpy.qos import ReliabilityPolicy, QoSProfile
from std_msgs.msg import String
import random

class HandlerNode(Node): # Mude o nome da classe

    def __init__(self):
        super().__init__('handler_node') # Mude o nome do nó
        self.timer = self.create_timer(0.25, self.control)

        # Subscribers
        self.sub_comando = self.create_subscription(String, 'comando', self.callback_comando, 10)

        # Publishers
        self.pub_comando = self.create_publisher(String, 'comando', 10)

        self.alvos = ['azul_10', 'verde_10', 'amarelo_10', 'azul_20', 'verde_20', 'amarelo_20']
        self.in_mission = False
    
    def callback_comando(self, msg):
        if msg.data == 'pronto':
            self.pub_comando.publish(String(data=random.choice(self.alvos)))
        elif msg.data == 'finalizado':
            self.pub_comando.publish(String(data='Muito bem!'))


    def control(self):
        print('running...')
        
            
def main(args=None):
    rclpy.init(args=args)
    ros_node = HandlerNode() # Mude o nome da classe

    rclpy.spin(ros_node)

    ros_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()