import asyncio
import uuid
import flet as ft
from gmqtt import Client as MQTTClient

# Configuração do Broker (Dados no código Arduino)
MQTT_BROKER = "hfb72712.ala.eu-central-1.emqxsl.com"
MQTT_PORT = 8883
MQTT_USER = "esp32"
MQTT_PASS = "123456"

class IndustryDashboard:
    def __init__(self, page: ft.Page):
        self.page = page
        self.client = None
        
        # Elementos de Interface (Labels de Monitoramento)
        self.temp_text = ft.Text("--- °C", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.vib_text = ft.Text("--- g", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        
        # Containers de Monitoramento (Guardados em variáveis para alterar o bgcolor depois)
        self.temp_container = ft.Container(
            content=ft.Column([ft.Text("Temperatura Atual"), self.temp_text], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, padding=20, border_radius=10, expand=True
        )
        self.vib_container = ft.Container(
            content=ft.Column([ft.Text("Vibração Atual"), self.vib_text], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, padding=20, border_radius=10, expand=True
        )
        
        # Inputs para os Limites
        self.input_max_temp = ft.TextField(label="Temp Máxima (°C)", value="40.0", width=140, keyboard_type=ft.KeyboardType.NUMBER)
        self.input_min_temp = ft.TextField(label="Temp Mínima (°C)", value="20.0", width=140, keyboard_type=ft.KeyboardType.NUMBER)
        self.input_vib_limit = ft.TextField(label="Limite Vibração (g)", value="2.5", width=140, keyboard_type=ft.KeyboardType.NUMBER)
        
        # Estado do Buzzer
        self.buzzer_state = False
        self.buzzer_btn = ft.Button(
            
            "Operar Buzzer", 
            icon=ft.Icons.VOLUME_UP, 
            on_click=self.toggle_buzzer, 
            style=ft.ButtonStyle(bgcolor=ft.Colors.RED_400, color=ft.Colors.WHITE)
        )

    async def connect_mqtt(self):
        """Inicializa e conecta o cliente MQTT assíncrono."""
        client_id = f"FletClient-{uuid.uuid4().hex[:6]}"
        self.client = MQTTClient(client_id)
        self.client.set_auth_credentials(MQTT_USER, MQTT_PASS)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        try:
            await self.client.connect(MQTT_BROKER, MQTT_PORT, ssl=True)
        except Exception as e:
            print(f"Erro ao conectar ao Broker: {e}")

    def on_connect(self, client, flags, rc, properties):
        self.page.show_dialog(ft.SnackBar(ft.Text("Conectado com sucesso ao Broker MQTT!",weight='bold', color='white'), bgcolor='green',))
        self.client.subscribe("industria4/telemetria/temp")
        self.client.subscribe("industria4/telemetria/vib")

    def on_message(self, client, topic, payload, qos, properties):
        """Processa as mensagens recebidas do ESP32 de forma segura e atualiza as cores."""
        try:
            data = payload.decode("utf-8")
            val_atual = float(data)
            
            async def update_ui(e):
                if topic == "industria4/telemetria/temp":
                    self.temp_text.value = f"{val_atual:.1f} °C"
                    
                    # Captura os limites atuais digitados nos inputs
                    lim_max = float(self.input_max_temp.value or 40.0)
                    lim_min = float(self.input_min_temp.value or 20.0)
                    
                    # Altera a cor do container de temperatura baseado nos limites
                    if val_atual > lim_max or val_atual < lim_min:
                        self.temp_container.bgcolor = ft.Colors.RED_ACCENT_700  # Perigo / Alerta
                    else:
                        self.temp_container.bgcolor = ft.Colors.GREEN_700  # Normal / Seguro
                        
                elif topic == "industria4/telemetria/vib":
                    self.vib_text.value = f"{val_atual:.2f} g"
                    
                    lim_vib = float(self.input_vib_limit.value or 2.5)
                    
                    # Altera a cor do container de vibração baseado no limite máximo
                    if val_atual >= lim_vib:
                        self.vib_container.bgcolor = ft.Colors.RED_ACCENT_700  # Crítico
                    else:
                        self.vib_container.bgcolor = ft.Colors.GREEN_700  # Seguro
                
                self.page.update()

            self.page.run_task(update_ui, None)
            
        except Exception as e:
            self.page.show_dialog(ft.SnackBar(ft.Text(f"Erro ao processar mensagem MQTT: {e}",weight='bold', color='white'), bgcolor='red',))
            
        
        return 0

    async def send_param(self, topic, value):
        if self.client and self.client.is_connected:
            self.client.publish(topic, str(value))
            self.show_snackbar(f"Enviado para {topic}: {value}")

    async def toggle_buzzer(self, e):
        self.buzzer_state = not self.buzzer_state
        cmd = "on" if self.buzzer_state else "off"
        self.buzzer_btn.text = "Desligar Buzzer" if self.buzzer_state else "Buzzer"
        
        self.buzzer_btn.style = ft.ButtonStyle(
            
            bgcolor=ft.Colors.GREEN if self.buzzer_state else ft.Colors.RED_400,
            color=ft.Colors.WHITE
        )
        
        asyncio.create_task(self.send_param("industria4/buzzer", cmd))
        self.page.update()

    def show_snackbar(self, message):
        self.page.show_dialog(ft.SnackBar(ft.Text(message, color='white', weight='bold'), open=True, bgcolor='blue')) # Ajustado para método moderno do Flet
        self.page.update()

    def build_ui(self):
        """Monta a estrutura visual responsiva e limpa da aplicação."""
        self.page.title = "Dashboard - Indústria 4.0"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 20
        
        # Cards de Monitoramento (Instanciados no construtor)
        monitor_cards = ft.Row(
            controls=[
                self.temp_container,
                self.vib_container,
            ],
            spacing=20
        )

        # Configurações de Limites
        config_limits = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Configuração de Limites Operacionais", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([self.input_max_temp, self.input_min_temp, self.input_vib_limit], spacing=10, wrap=True),
                    ft.Button(
                        "Atualizar Limites no ESP32", 
                        icon=ft.Icons.SAVE,
                        on_click=lambda e: asyncio.create_task(self.update_all_limits())
                    )
                ]),
                padding=20
            )
        )

        # Painel de Controle Remoto
        control_panel = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Ações de Controle Atuarial", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Button("Corrigir Temperatura", icon=ft.Icons.THERMOSTAT, on_click=lambda e: asyncio.create_task(self.send_param("industria4/control/temp", "1"))),
                        ft.Button("Estabilizar Vibração", icon=ft.Icons.VIBRATION, on_click=lambda e: asyncio.create_task(self.send_param("industria4/control/vib", "1"))),
                        self.buzzer_btn
                    ], wrap=True, spacing=15)
                ]),
                padding=20
            )
        )

        # Adiciona tudo na tela principal
        self.page.add(
            ft.Container(height=20),
            ft.Text("Gerenciamento Industrial", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            monitor_cards,
            ft.Text("Painel de Comandos", size=20, weight=ft.FontWeight.W_500),
            config_limits,
            control_panel
        )

    async def update_all_limits(self):
        """Envia simultaneamente os 3 limites textuais para o dispositivo."""
        await self.send_param("industria4/tempMax", self.input_max_temp.value)
        await self.send_param("industria4/tempMin", self.input_min_temp.value)
        await self.send_param("industria4/vibLimit", self.input_vib_limit.value)


async def main(page: ft.Page):
    dashboard = IndustryDashboard(page)
    dashboard.build_ui()
    await dashboard.connect_mqtt()

if __name__ == "__main__":
    ft.run(main)
