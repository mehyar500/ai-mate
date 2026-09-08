class LocalRecorder extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const channel=inputs[0]?.[0]; if(channel)this.port.postMessage(channel.slice());
    // Leave output silent: microphone audio is never echoed to the speakers.
    return true;
  }
}
registerProcessor("local-recorder",LocalRecorder);
