from opentelemetry.trace import get_tracer
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

class EventLogger:
    TIME_TO_FIRST_TOKEN = "time_to_first_token"
    TIME_TO_FIRST_EXTENSION_CALL = "time_to_first_extension_call"
    TIME_TO_RUN_LOOP = "time_to_start_run_loop"
    TIME_TO_COMPLETE_RUN_LOOP = "time_to_complete_run_loop"

    def __init__(self):
        self.tracer = get_tracer(__name__)
        self.spans = {}
        self.completed_spans = {}

    def start_span(self, name: str):
        if name in self.spans:
            return self.spans[name]
        else:
            span = self.tracer.start_span(name)
            self.spans[name] = span
            return span

    def end_span(self, name: str):
        if name in self.spans:
            self.spans[name].end()
            self.completed_spans[name] = self.spans[name]
            del self.spans[name]

    def report(self):
        return {
            name: span.to_json() for name, span in self.completed_spans.items()
        }
