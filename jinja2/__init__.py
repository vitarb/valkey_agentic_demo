from string import Template


class Template(Template):
    def render(self, **kwargs):
        return self.safe_substitute(**kwargs)
