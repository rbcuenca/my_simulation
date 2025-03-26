import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from robcomp_interfaces.msg import GameStatus
import time
import random

class GameStateNode(Node):

    def __init__(self):
        super().__init__('game_state_node')
        self.timer = self.create_timer(0.25, self.control)

        self.twist = Twist()
        self.is_moving = False
        self.is_ready = False
        self.start_time = None
        self.current_word_index = 0
        self.current_lost_index = 0
        self.words = ["bata", "ta", "tinha", "fri", "ta", "1", "2", "3"]
        self.msg = GameStatus()
        self.robot_state = 'finished'
        self.wait_start_time = None
        self.wait_duration = None

        self.lost_msg = GameStatus()
        self.lost_msg.status = "LOST"
        self.lost_msg.current_word = "Você perdeu!"
        self.lost_msg.player_name = "System"

        self.win_msg = GameStatus()
        self.win_msg.status = "WON"
        self.win_msg.player_name = "System"

        self.state_machine = {
            'waiting': self.state_waiting,
            'playing': self.state_playing,
            'lost': self.state_lost,
            'finished': self.state_finished
        }

        qos_reliable = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        qos_best_effort = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.status_publisher = self.create_publisher(GameStatus, 'young_hee', 10)
        self.cmd_vel_publisher = self.create_publisher(Twist, '/cmd_vel', 10)

        self.create_subscription(Twist, '/cmd_vel', self.velocity_callback, qos_reliable)
        self.create_subscription(GameStatus, 'young_hee', self.status_callback, qos_reliable)
        self.create_subscription(Odometry, '/odom', self.odom_callback, qos_best_effort)

    def velocity_callback(self, msg):
        self.is_moving = msg.linear.x >= 0.05 or msg.angular.z >= 0.05

    def status_callback(self, msg):
        self.msg = msg
        if msg.status == "READY":
            self.start_time = msg.start_time
            self.get_logger().info(f"Jogo iniciado por {msg.player_name} às {self.start_time}")
            self.robot_state = 'playing'
            self.current_word_index = 0

    def odom_callback(self, msg):
        self.x = msg.pose.pose.position.x

    def state_playing(self):
        if self.current_word_index >= len(self.words):
            self.current_word_index = 0
            return
        
        if self.x <= -5.0 and self.start_time is not None:
            completion_time = time.time() - self.start_time
            self.robot_state = 'finished'
            self.get_logger().info(f"Parabéns! Você completou o jogo em {completion_time:.2f} segundos.")
            self.win_msg.current_word = f"Parabéns! Você completou o jogo em {completion_time:.2f} segundos."
            self.status_publisher.publish(self.win_msg)
            return

        word = self.words[self.current_word_index]
        msg = GameStatus()
        msg.status = "IN_PROGRESS"
        msg.current_word = word
        msg.player_name = "System"
        msg.start_time = self.start_time
        self.status_publisher.publish(msg)
        # self.get_logger().info(f'Palavra publicada: {word}')

        if word == "3":
            self.robot_state = 'waiting'
            self.wait_start_time = time.time()
            self.wait_duration = random.uniform(2.0, 4.0)
            return
        else:
            self.current_word_index += 1
            time.sleep(random.uniform(0.5, 2))

    def state_waiting(self):
        if self.is_moving:
            self.robot_state = 'lost'
            return
        
        elapsed = time.time() - self.wait_start_time
        if elapsed >= self.wait_duration:
            self.robot_state = 'playing'
            self.current_word_index += 1

    def state_lost(self):
        self.status_publisher.publish(self.lost_msg)
        self.get_logger().info("Publicado: Você perdeu!")

        twist = Twist()
        twist.linear.x = -2.0
        twist.angular.z = -2.0
        self.cmd_vel_publisher.publish(twist)
        time.sleep(0.5)

        self.current_lost_index += 1
        if self.current_lost_index >= 5:
            self.robot_state = 'finished'

    def state_finished(self):
        pass

    def control(self):
        # self.get_logger().info(f"[STATE] Estado atual: {self.robot_state}")
        self.state_machine[self.robot_state]()

def main(args=None):
    rclpy.init(args=args)
    node = GameStateNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
