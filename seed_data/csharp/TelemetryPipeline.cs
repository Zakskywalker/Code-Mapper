using System;
using System.Collections.Generic;

namespace Seed.Telemetry {
    public interface IProcessor {
        string Name { get; }
        TelemetryEvent Process(TelemetryEvent input);
    }

    public class TelemetryPipeline {
        private readonly List<IProcessor> _processors = new();

        public void Add(IProcessor processor) {
            _processors.Add(processor);
        }

        public TelemetryEvent Run(TelemetryEvent evt) {
            foreach (var p in _processors) {
                evt = p.Process(evt);
            }
            return evt;
        }
    }

    public record TelemetryEvent(string Type, DateTime Timestamp, Dictionary<string,string> Payload);
}
