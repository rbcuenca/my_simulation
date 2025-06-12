import rclpy
from rclpy.node import Node
from rclpy.qos import ReliabilityPolicy, QoSProfile
from std_msgs.msg import String
import random
import time

# ros2 launch my_gazebo retangulos.launch.py

class HandlerNode(Node): # Mude o nome da classe

    def __init__(self):
        super().__init__('animal_node') # Mude o nome do nó
        self.timer = self.create_timer(0.25, self.control)

        # Subscribers
        self.sub_animal = self.create_subscription(String, 'animal', self.callback_animal, 10)

        # Publishers
        self.pub_animal = self.create_publisher(String, 'animal', 10)

        self.alvos = ['dog', 'cat', 'horse']
        self.in_mission = False
    
    def callback_animal(self, msg):
        if msg.data == 'completei':
            # wait between 1 and 5 seconds
            time.sleep(random.randint(1, 10))
            self.pub_animal.publish(String(data=random.choice(self.alvos)))


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