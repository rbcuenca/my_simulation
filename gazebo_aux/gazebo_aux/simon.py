import math
import random
import rclpy
from rclpy.node import Node
from rclpy.qos import ReliabilityPolicy, QoSProfile
from rclpy.duration import Duration
from gazebo_aux.odom import Odom
from gazebo_aux.laser import Laser
from robcomp_interfaces.msg import SimonSaysMSG


class Simon(Node, Odom, Laser):
    def __init__(self):
        super().__init__('simon_node')
        Odom.__init__(self)
        Laser.__init__(self)
        rclpy.spin_once(self)

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.pub = self.create_publisher(SimonSaysMSG, '/simon_says', 10)
        self.sub = self.create_subscription(SimonSaysMSG, '/simon_says', self.simon_cb, qos)

        self.robot_state = 'aguarda_ready'
        self.state_machine = {
            'aguarda_ready': self.aguarda_ready,
            'aguarda_opcoes': self.aguarda_opcoes,
            'espera_antes_responder': self.espera_antes_responder,
            'envia_comando': self.envia_comando,
            'aguarda_execucao': self.aguarda_execucao,
            'publica_lost': self.publica_lost,
            'publica_win': self.publica_win,
            'fim': self.fim,
        }

        self.student_name = ''
        self.game_mode = 'aleatorio'
        self.ready_time = None
        self.last_robot_options = None

        self.pending_deadline = None
        self.post_trick_deadline = None
        self.pending_command_text = ''
        self.pending_turn_side = None
        self.last_command_was_valid = False
        self.waiting_robot_reaction = False

        self.pre_command_x = None
        self.pre_command_y = None
        self.pre_command_yaw = None
        self.reaction_deadline = None
        self.min_linear_move = 0.03
        self.min_angular_move = math.radians(8.0)
        self.max_reaction_time = 8.0
        self.last_lost_pub = None
        self.has_ever_tried_to_trick = False

        self.deterministic_sequence = ['direita', 'direita', 'direita', 'direita', 'esquerda']
        self.deterministic_index = 0

        self.timer = self.create_timer(0.05, self.control)
        self.get_logger().info('Simon iniciado. Aguardando READY...')

    def _reset_game_state(self, keep_student_name=True):
        current_name = self.student_name if keep_student_name else ''
        self.student_name = current_name
        self.game_mode = 'aleatorio'
        self.ready_time = None
        self.last_robot_options = None
        self.pending_deadline = None
        self.post_trick_deadline = None
        self.pending_command_text = ''
        self.pending_turn_side = None
        self.last_command_was_valid = False
        self.waiting_robot_reaction = False
        self.pre_command_x = None
        self.pre_command_y = None
        self.pre_command_yaw = None
        self.reaction_deadline = None
        self.has_ever_tried_to_trick = False
        self.deterministic_index = 0
        self.last_lost_pub = None

    def _now_float(self):
        t = self.get_clock().now().to_msg()
        return float(t.sec) + float(t.nanosec) * 1e-9

    def _normalize_angle(self, angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def _robot_is_moving(self):
        return abs(float(self.vx)) > 0.02 or abs(float(self.vw)) > 0.05

    def _robot_has_changed_pose_since_command(self):
        if self.pre_command_x is None or self.pre_command_y is None or self.pre_command_yaw is None:
            return False

        dx = float(self.x) - self.pre_command_x
        dy = float(self.y) - self.pre_command_y
        dlin = math.hypot(dx, dy)
        dyaw = abs(self._normalize_angle(float(self.yaw) - self.pre_command_yaw))
        return dlin >= self.min_linear_move or dyaw >= self.min_angular_move

    def _publish(self, status='', lados='', comando='', modo_de_jogo=''):
        msg = SimonSaysMSG()
        msg.student_name = self.student_name or 'N/A'
        msg.horario = self._now_float()
        msg.status = status
        msg.lados = lados
        msg.comando = comando
        msg.modo_de_jogo = modo_de_jogo
        self.pub.publish(msg)

    def _extract_robot_text(self, msg):
        if msg.comando:
            return msg.comando.strip().lower()
        if msg.lados:
            return msg.lados.strip().lower()
        if msg.status:
            return msg.status.strip().lower()
        return ''

    def _side_is_free(self, side_values):
        try:
            return min(side_values) > 0.6
        except Exception:
            return False

    def _expected_options_here(self):
        left_free = self._side_is_free(self.left)
        right_free = self._side_is_free(self.right)

        if right_free and left_free:
            return 'direita e esquerda'
        if right_free:
            return 'direita'
        if left_free:
            return 'esquerda'
        return 'nenhuma'

    def _valid_choices_from_options(self, options_str):
        if options_str == 'direita e esquerda':
            return ['direita', 'esquerda']
        if options_str == 'direita':
            return ['direita']
        if options_str == 'esquerda':
            return ['esquerda']
        return []

    def _should_trick_now(self): # Ajustar a probabilidade de pegadinha conforme o histórico
        p = 0.10 if self.has_ever_tried_to_trick else 0.40
        return random.random() < p

    def _response_delay(self):
        return random.uniform(0.5, 1.5)

    def _post_invalid_command_delay(self):
        return random.uniform(2.0, 4.0)

    def _build_invalid_command_for(self, valid_choices):
        side = random.choice(valid_choices) if valid_choices else 'direita'
        if side == 'esquerda':
            return 'vire para a esquerda'
        return 'vire para a direita'

    def _build_valid_command_for(self, side):
        if side == 'esquerda':
            return 'Simon diz: vire para a esquerda'
        return 'Simon diz: vire para a direita'

    def _pick_next_valid_side(self, valid_choices):
        if not valid_choices:
            return None

        if self.game_mode == 'deterministico':
            if self.deterministic_index >= len(self.deterministic_sequence):
                return None
            side = self.deterministic_sequence[self.deterministic_index]
            if side not in valid_choices:
                return None
            return side

        return random.choice(valid_choices)

    def simon_cb(self, msg):
        text = self._extract_robot_text(msg)

        if msg.student_name:
            self.student_name = msg.student_name

        if text == 'simon, eu estou pronto' or msg.status.strip().upper() == 'READY':
            self._reset_game_state()
            self.game_mode = 'deterministico' if msg.modo_de_jogo.strip().lower() == 'deterministico' else 'aleatorio'
            self.ready_time = self._now_float()
            self.robot_state = 'aguarda_opcoes'
            self.get_logger().info(f'READY recebido de {self.student_name}. Modo={self.game_mode}')
            return

        if msg.status.strip().upper() in ['LOST', 'WIN']:
            return

        if msg.status.strip().upper() == 'IN_PROGRESS' and msg.comando:
            return

        known_options = ['direita e esquerda', 'direita', 'esquerda', 'nenhuma']
        if text in known_options and self.robot_state in ['aguarda_opcoes', 'aguarda_execucao']:
            self.last_robot_options = text
            expected = self._expected_options_here()

            if text != expected:
                self.get_logger().warn(f'Lados incorretos: recebido={text} esperado={expected}')
                self.robot_state = 'publica_lost'
                return

            if text == 'nenhuma':
                self.robot_state = 'publica_win'
                return

            self.pending_deadline = self.get_clock().now() + Duration(seconds=self._response_delay())
            self.robot_state = 'espera_antes_responder'

    def aguarda_ready(self):
        pass

    def aguarda_opcoes(self):
        pass

    def espera_antes_responder(self):
        if self.pending_deadline is None or self.get_clock().now() < self.pending_deadline:
            return

        valid_choices = self._valid_choices_from_options(self.last_robot_options or '')

        if self.game_mode == 'deterministico':
            side = self._pick_next_valid_side(valid_choices)
            if side is None:
                self.robot_state = 'publica_lost'
                return

            self.pending_turn_side = side
            self.pending_command_text = self._build_valid_command_for(side)
            self.last_command_was_valid = True
            self.robot_state = 'envia_comando'
            return

        if self._should_trick_now():
            self.pending_command_text = self._build_invalid_command_for(valid_choices)
            self.pending_turn_side = None
            self.last_command_was_valid = False
            self.has_ever_tried_to_trick = True
            self.post_trick_deadline = None
            self.robot_state = 'envia_comando'
            return

        side = self._pick_next_valid_side(valid_choices)
        if side is None:
            self.robot_state = 'publica_lost'
            return

        self.pending_turn_side = side
        self.pending_command_text = self._build_valid_command_for(side)
        self.last_command_was_valid = True
        self.robot_state = 'envia_comando'

    def envia_comando(self):
        if not self.pending_command_text:
            self.robot_state = 'publica_lost'
            return

        self.get_logger().info(f'Publicando comando: {self.pending_command_text}')
        self._publish(status='IN_PROGRESS', comando=self.pending_command_text)

        self.pre_command_x = float(self.x)
        self.pre_command_y = float(self.y)
        self.pre_command_yaw = float(self.yaw)
        self.reaction_deadline = self.get_clock().now() + Duration(seconds=self.max_reaction_time)

        if self.last_command_was_valid:
            self.waiting_robot_reaction = True
        else:
            self.waiting_robot_reaction = True
            self.post_trick_deadline = self.get_clock().now() + Duration(seconds=self._post_invalid_command_delay())

        self.robot_state = 'aguarda_execucao'

    def _seconds_until(self, deadline):
        if deadline is None:
            return 0.0
        remaining = deadline - self.get_clock().now()
        return max(0.0, remaining.nanoseconds / 1e9)

    def aguarda_execucao(self):
        if not self.waiting_robot_reaction:
            self.robot_state = 'aguarda_opcoes'
            return

        moved = self._robot_is_moving() or self._robot_has_changed_pose_since_command()

        if not self.last_command_was_valid:
            if moved:
                self.get_logger().warn('Robô se moveu após comando sem Simon diz.')
                self.robot_state = 'publica_lost'
                return

            if self.post_trick_deadline is None:
                self.post_trick_deadline = self.get_clock().now() + Duration(seconds=self._post_invalid_command_delay())
                return

            if self.get_clock().now() >= self.post_trick_deadline:
                self.waiting_robot_reaction = False
                self.pending_command_text = ''
                self.pending_turn_side = None
                self.last_command_was_valid = False
                self.post_trick_deadline = None
                self.pending_deadline = self.get_clock().now() + Duration(seconds=self._response_delay())
                self.robot_state = 'espera_antes_responder'
            return

        if moved:
            self.waiting_robot_reaction = False
            if self.game_mode == 'deterministico':
                self.deterministic_index += 1
            self.pending_command_text = ''
            self.pending_turn_side = None
            self.last_command_was_valid = False
            self.robot_state = 'aguarda_opcoes'
            return

        if self.reaction_deadline is not None and self.get_clock().now() >= self.reaction_deadline:
            self.get_logger().warn('Robô não reagiu a um comando válido.')
            self.robot_state = 'publica_lost'

    def publica_lost(self):
        now = self.get_clock().now()
        if self.last_lost_pub is None or (now - self.last_lost_pub) >= Duration(seconds=1.0):
            self._publish(status='LOST', comando='voce perdeu')
            self.last_lost_pub = now
        self._reset_game_state()
        self.robot_state = 'aguarda_ready'
        self.get_logger().info('Aguardando novo READY para reiniciar o jogo.')

    def publica_win(self):
        elapsed = 0.0 if self.ready_time is None else self._now_float() - self.ready_time
        self.get_logger().info(f'{self.student_name} venceu em {elapsed:.2f}s')
        self._publish(status='WIN', comando=f'{self.student_name} venceu em {elapsed:.2f}s')
        self.robot_state = 'fim'

    def fim(self):
        pass

    def control(self):
        self.state_machine[self.robot_state]()


def main(args=None):
    rclpy.init(args=args)
    ros_node = Simon()

    try:
        while rclpy.ok():
            rclpy.spin_once(ros_node)
            if ros_node.robot_state == 'fim':
                break
    finally:
        ros_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()