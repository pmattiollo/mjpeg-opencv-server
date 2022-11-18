from threading import Thread
import time
import requests


class Control:

    def __init__(self, server_url):
        self.server_url = server_url
        self.command = None
        self.command_thread = Thread(target=self.send_command)
        self.command_thread.start()

    def get_sensor_data(self):
        resp = requests.get(url=f'{self.server_url}/sensors')
        return resp.json()

    def set_motors(self, fl, rl, fr, rr):
        data = {'front_left': fl,
                'rear_left': rl,
                'front_right': fr,
                'rear_right': rr}

        self.command = ('motor',data)


    def send_command(self):
        while True:
            try:
                if self.command is not None:
                    resp = requests.post(url=f'{self.server_url}/{self.command[0]}', json=self.command[1])
                    if resp.status_code != 204:
                        print(resp.text)
                    self.command = None
            except:
                pass
            time.sleep(0.1)
