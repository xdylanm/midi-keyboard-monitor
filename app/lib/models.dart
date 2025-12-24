class NoteEvent {
  final bool isNoteOn;
  final int channel;
  final int note;
  final int velocity;
  final int tsMs;

  NoteEvent({
    required this.isNoteOn,
    required this.channel,
    required this.note,
    required this.velocity,
    required this.tsMs,
  });

  @override
  String toString() => 'NoteEvent(${isNoteOn ? 'ON' : 'OFF'} ch:$channel n:$note v:$velocity ts:$tsMs)';
}
