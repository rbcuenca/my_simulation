import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from custom_msgs.msg import GameStatus  # Nova mensagem customizada
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import random
import time

class YoungHeeNode(Node):
    def __init__(self):
        super().__init__('young_hee_node')
        self.publisher = self.create_publisher(GameStatus, 'young-hee', QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))
        self.cmd_vel_publisher = self.create_publisher(Twist, '/cmd_vel', QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.subscription_cmd_vel = self.create_subscription(Twist, '/cmd_vel', self.velocity_callback, QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.subscription_ready = self.create_subscription(GameStatus, 'young-hee', self.ready_callback, QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))
        self.subscription_odom = self.create_subscription(Odometry, '/odom', self.odom_callback, QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
        
        self.is_moving = False
        self.is_ready = False
        self.start_time = None
        self.words = ["bata", "ta", "tinha", "fri", "ta", "1", "2", "3"]
        self.msg.status == "LOST"
    
    def velocity_callback(self, msg):
        # Verifica se o TurtleBot está se movendo
        self.is_moving = msg.linear.x != 0.0 or msg.angular.z != 0.0
    
    def ready_callback(self, msg):
        self.msg.status = msg.status
        if self.msg.status == "READY":
            self.is_ready = False
            self.start_time = msg.start_time  # Usa o tempo enviado pelo jogador
            self.get_logger().info(f"Jogo iniciado pelo jogador: {msg.player_name} às {self.start_time}")
            
        if self.msg.status == "LOST":
            self.is_ready = False
            self.get_logger().info("Jogo encerrado.")
        if self.msg.status == "IN_PROGRESS":
            self.play_game()
            self.is_ready = True
            self.get_logger().info("Jogo em andamento.")
    
    def odom_callback(self, msg):
        # Verifica se o jogador chegou na posição y = 10m
        if msg.pose.pose.position.y >= 10.0 and self.start_time is not None:
            completion_time = time.time() - self.start_time
            self.get_logger().info(f"Parabéns! Você completou o jogo em {completion_time:.2f} segundos.")
            self.start_time = None  # Reseta para evitar múltiplas mensagens
    
    def play_game(self):
        if not self.is_ready:
            return
        
        while self.msg.status == "IN_PROGRESS":
            for word in self.words:
                msg = GameStatus()
                msg.status = "IN_PROGRESS"
                msg.current_word = word
                msg.player_name = "Sistema"
                msg.start_time = self.start_time
                self.publisher.publish(msg)
                self.get_logger().info(f'Published: {word}')
                time.sleep(random.uniform(0.5, 2.0))  # Espera aleatória
                
                # Se o TurtleBot estiver em movimento ao publicar "3"
                if word == "3" and self.is_moving:
                    status = ["IN_PROGRESS","IN_PROGRESS","IN_PROGRESS","IN_PROGRESS","LOST"]
                    for i in range(5):
                        msg = GameStatus()
                        msg.status = status[i]
                        msg.current_word = "Você perdeu!"
                        msg.player_name = "Sistema"
                        msg.start_time = self.start_time
                        self.publisher.publish(msg)
                        self.get_logger().info('Published: Você perdeu!')
                        time.sleep(0.5)
                      
                        # Publica uma velocidade negativa grande no linear e na orientação
                        twist_msg = Twist()
                        twist_msg.linear.x = -2.0  # Movimento para trás
                        twist_msg.angular.z = -2.0  # Rotação intensa
                        self.cmd_vel_publisher.publish(twist_msg)
                    return  # Sai do loop se perdeu

def main(args=None):
    rclpy.init(args=args)
    node = YoungHeeNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
