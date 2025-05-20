from jinja2 import Template


def render() -> str:
    tpl = Template("#!/bin/bash\necho setup\n$marker\n")
    result = tpl.render(marker="### USERDATA OK ###")
    return result
