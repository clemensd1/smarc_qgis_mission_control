import re
import json
from uuid import UUID, uuid4
from dataclasses import dataclass
from copy import deepcopy

from qgis.PyQt.QtCore import QObject, pyqtSlot, pyqtSignal

# Import bundled MQTT
import os, sys
path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'third_party')
sys.path.insert(0, path)
import paho.mqtt.client as mqtt

from ..compat import StrEnum
from ..domain.waraps import *
from ..domain.waypoints import GeoPoint
from ..domain.missionplan import MissionPlan


@dataclass
class VehicleEvent:
    vehicleTopic: str

@dataclass
class VehicleHeartbeatEvent(VehicleEvent):
    mode: str | None = "Mode"
    pass

@dataclass
class VehicleSensorEvent(VehicleEvent):
    position: GeoPoint | None = None
    heading: float | None = None
    course: float | None = None
    depth: float | None = None
    speed: float | None = None
    roll: float | None = None
    pitch: float | None = None

@dataclass
class VehicleTaskStateEvent(VehicleEvent):
    tasksAvailable: list[WaraPsAvailableTask]
    tasksExecuting: list[WaraPsExecutingTask]

class MqttConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"

class MqttService(QObject):
    connectionStateChanged = pyqtSignal(MqttConnectionState)
    vehicleHeartbeat = pyqtSignal(VehicleHeartbeatEvent)
    vehicleSensorEvent = pyqtSignal(VehicleSensorEvent)
    vehicleTaskStateEvent = pyqtSignal(VehicleTaskStateEvent)

    _client: mqtt.Client | None
    _context: str
    _vehicles: dict[str, dict]

    mqttTopicPattern = re.compile(
        r'([^/]+)/unit/(air|surface|subsurface)/(real|simulation)/([^/]+)(/.+)$'
    )

    def __init__(self, parent: QObject | None):
        super().__init__(parent)
        self._client = None
        self._context = ""
        self._vehicles: dict[str, dict] = {}

    def connect(self, ip: str, port: int, username: str | None, password: str | None,
                context: str):
        self.disconnect()

        self._context = context

        # TODO: username/password/TLS

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self.onMqttConnect
        self._client.on_disconnect = self.onMqttDisconnect
        self._client.on_message = self.onMqttMessage
        self._client.connect_async(ip, port)
        self._client.loop_start()

    def disconnect(self):
        if self._client is None:
            return

        try:
            self._client.disconnect()
        finally:
            self._client.loop_stop()
            self._client = None

    def onMqttConnect(self, client, userdata, flags, reason_code, properties):
        print('connected')
        print('subscribing to', self._context)
        client.subscribe(self._context)
        self.connectionStateChanged.emit(MqttConnectionState.CONNECTED)

    def onMqttDisconnect(self, client, userdata, flags, reason_code, properties):
        print('disconnected')
        self.connectionStateChanged.emit(MqttConnectionState.DISCONNECTED)

    def onMqttMessage(self, client, userdata, message):
        match = self.mqttTopicPattern.match(message.topic)
        if not match:
            # Not something we support yet
            return
        root, domain, mode, vehicleName, vehicleSubtopic = match.groups()

        # Reconstruct vehicle topic
        vehicleTopic = f'{root}/unit/{domain}/{mode}/{vehicleName}'

        if vehicleSubtopic == r'/heartbeat':
            data = json.loads(message.payload)
            event = VehicleHeartbeatEvent(
                vehicleTopic = vehicleTopic,
            )
            event.mode = mode
            
            print(event)
            self.vehicleHeartbeat.emit(event)
        elif (match := re.match(r'/sensor/([^/]+)$', vehicleSubtopic)) is not None:
            if not vehicleTopic in self._vehicles:
                self._vehicles[vehicleTopic] = {
                    'sensor': VehicleSensorEvent(vehicleTopic)
                }
            vehicleSensorEvent = self._vehicles[vehicleTopic]['sensor']

            sensor = match.group(1)
            if sensor == 'position':
                data = json.loads(message.payload)
                # Our GeoPoint class expects tolerance, but it is not a standard WARA-PS
                # field, so we mock it to 0. Also, we expect rostype instead of type
                # TODO: carry position not as GeoPoint
                data['tolerance'] = 0
                data['rostype'] = data.pop('type')
                point = GeoPoint.fromJson(data)

                vehicleSensorEvent.position = point

                # print(vehicleSensorEvent)
                # TODO: emit sensor events even if position was not updated?
                self.vehicleSensorEvent.emit(deepcopy(vehicleSensorEvent))
            elif sensor in ['heading', 'course', 'depth', 'speed', 'roll', 'pitch']:
                setattr(vehicleSensorEvent, sensor, float(message.payload))
            elif sensor in ['bt', 'executing_tasks']:
                # explicitly unhandled sensors
                ...
            else:
                # unsupported sensor!
                print(f'unsupported sensor', sensor)
        elif vehicleSubtopic == '/tst_execution_info':
            data = json.loads(message.payload)
            tasksExecuting = [
                WaraPsExecutingTask(
                    description=task['description'],
                    type=task['task-name'],
                    status=task['status'],
                    uuid=UUID(task['task-uuid'])
                ) for task in data['tasks-executing']
            ]
            event = VehicleTaskStateEvent(
                # TODO
                vehicleTopic=vehicleTopic,
                tasksAvailable=[],
                tasksExecuting=tasksExecuting,
            )
            self.vehicleTaskStateEvent.emit(event)
        else:
            # unsupported vehicle subtopic!
            ...

    @pyqtSlot(MissionPlan, set)
    def onPublishMissionPlan(self, plan: MissionPlan, vehicleTopics: set[str]):
        if self._client is None:
            # TODO
            return
        for vehicleTopic in vehicleTopics:
            self.publishMissionPlan(plan, vehicleTopic)

    def publishMissionPlan(self, plan: MissionPlan, vehicleTopic: str):
        if self._client is None:
            # TODO
            return
        topic = f'{vehicleTopic}/tst/command'
        receiver = vehicleTopic.split('/')[-1]
        data = {
            "receiver": receiver,
            "command": "start-tst",
            "tst": plan.toJson() | {
                "common-params": {
                    "execunit": f"/{receiver}",
                    "node-uuid": str(uuid4()),
                },
            },
            "com-uuid": str(uuid4()),
            "sender": "QGIS-MissionControl",
        }
        self._client.publish(topic, json.dumps(data))

    @pyqtSlot(set)
    def onEmergencySignal(self, vehicleTopics: set[str]):
        if self._client is None:
            # TODO
            return
        for vehicleTopic in vehicleTopics:
            self.publishEmergencySignal(vehicleTopic)

    def publishEmergencySignal(self, vehicleTopic: str):
        if self._client is None:
            # TODO
            return
        topic = f'{vehicleTopic}/tst/command'
        receiver = vehicleTopic.split('/')[-1]
        data = {
            'receiver': receiver,
            'signal': '$abort',
            'unit': f'/{receiver}',
            'command': 'signal-unit',
            'com-uuid': str(uuid4()),
            'sender': 'QGIS-MissionControl',
        }
        self._client.publish(topic, json.dumps(data))
