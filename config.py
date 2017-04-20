import yaml

class Config:
    @classmethod
    def register(cls, key):
        return property(
            lambda self: self.yaml[key],
            lambda self, value: self.save(key, value),
        )

    def __init__(self, path):
        self.path = path

        with open(self.path) as file:
            self.yaml = yaml.load(file)

    def save(self, key, value):
        if key in self.yaml and self.yaml[key] == value:
            return

        self.yaml[key] = value
        with open(self.path, 'w') as file:
            file.write(yaml.dump(self.yaml, default_flow_style=False))
