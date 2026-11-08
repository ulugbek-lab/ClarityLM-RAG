def format_source(source: dict, max_chars: int = 800, max_lines: int = 40) -> dict:
    text = source.get('text', '')
    path = source.get('metadata', {}).get('path')
    if text:
        text = _trim_source_text(text, max_chars=max_chars, max_lines=max_lines)
        lang = 'text'
        if path and '.' in path:
            lang = path.rsplit('.', 1)[-1]
        source = dict(source)
        source['text'] = f'```{lang}\n{text}\n```'
    return source


def _trim_source_text(text: str, max_chars: int, max_lines: int) -> str:
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ['...']
    trimmed = '\n'.join(lines)
    if len(trimmed) > max_chars:
        trimmed = trimmed[:max_chars].rstrip() + '\n...'
    return trimmed
