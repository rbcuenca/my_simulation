# gamemaster.py
import rclpy
import random
from rclpy.node import Node
from robcomp_interfaces.msg import GameMaster

class GameMasterNode(Node):

    def __init__(self):
        super().__init__('gamemaster_node')

        self.robot_state = 'espera_ready'
        self.state_machine = {
            'espera_ready': self.espera_ready,
            'espera_tempo': self.espera_tempo,
            'manda_ir_objeto': self.manda_ir_objeto,
            'done': self.done,
        }

        self.recebeu_ready = False
        self.nome_aluno = ''
        self.time_to_next = None  
        self.dt = 0.1 

        self.gm_sub = self.create_subscription(
            GameMaster,
            '/gamemaster',
            self.gamemaster_callback,
            10
        )

        self.gm_pub = self.create_publisher(
            GameMaster,
            '/gamemaster',
            10
        )

        self.timer = self.create_timer(self.dt, self.control)

    def gamemaster_callback(self, msg: GameMaster):
        if msg.status == 'READY':
            self.recebeu_ready = True
            self.nome_aluno = msg.aluno

    def espera_ready(self):
        if self.recebeu_ready:
            self.get_logger().info(f'Jogador READY de {self.nome_aluno}')
            self.recebeu_ready = False

            self.time_to_next = random.uniform(50.0, 80.0)
            self.robot_state = 'espera_tempo'

    def espera_tempo(self):
        if self.time_to_next is None:
            self.time_to_next = random.uniform(50.0, 80.0)

        self.time_to_next -= self.dt

        if self.time_to_next <= 0.0:
            self.robot_state = 'manda_ir_objeto'

    def manda_ir_objeto(self):
        msg = GameMaster()
        msg.status = 'VAI_PRO_OBJETO'
        msg.aluno = ''
        msg.timestamp = self.get_clock().now().to_msg()

        self.get_logger().info('Enviando comando: VAI_PRO_OBJETO')
        self.gm_pub.publish(msg)

        self.time_to_next = random.uniform(50.0, 80.0)
        self.robot_state = 'espera_tempo'

    def done(self):
        pass

    def control(self):
        self.state_machine[self.robot_state]()

def main(args=None):
    rclpy.init(args=args)
    node = GameMasterNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
