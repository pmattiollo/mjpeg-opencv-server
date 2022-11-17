import requests


class Control:

    def __init__(self, server_url):
        self.server_url = server_url

    def get_sensor_data(self):
        resp = requests.get(url=f'{self.server_url}/sensors')
        return resp.json()

    def set_motors(self, fl, rl, fr, rr):
        data = {'front_left': fl,
                'rear_left': rl,
                'front_right': fr,
                'rear_right': rr}

        resp = requests.post(url=f'{self.server_url}/motor', json=data)
        if resp.status_code != 204:
            print(resp.text)

