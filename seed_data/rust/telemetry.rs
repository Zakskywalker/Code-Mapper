use std::collections::HashMap;

pub struct TelemetryEvent {
    pub kind: String,
    pub payload: HashMap<String, String>,
}

pub trait Processor {
    fn name(&self) -> &str;
    fn process(&self, input: TelemetryEvent) -> TelemetryEvent;
}

pub struct Pipeline {
    processors: Vec<Box<dyn Processor>>,
}

impl Pipeline {
    pub fn new() -> Self {
        Self { processors: Vec::new() }
    }

    pub fn add(&mut self, processor: Box<dyn Processor>) {
        self.processors.push(processor);
    }

    pub fn run(&self, mut evt: TelemetryEvent) -> TelemetryEvent {
        for p in &self.processors {
            evt = p.process(evt);
        }
        evt
    }
}
