import 'package:flutter/material.dart';
import 'models.dart';

class VelocityView extends StatefulWidget {
  final List<NoteEvent> recent;
  final NoteEvent? latest;

  const VelocityView({Key? key, this.recent = const [], this.latest}) : super(key: key);

  @override
  State<VelocityView> createState() => _VelocityViewState();
}

class _VelocityViewState extends State<VelocityView> {
  @override
  Widget build(BuildContext context) {
    final v = widget.latest?.velocity ?? 0;
    final pct = (v / 127.0).clamp(0.0, 1.0);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(widget.latest?.isNoteOn == true ? 'Note On' : 'Idle', style: TextStyle(fontSize: 18)),
        SizedBox(height: 8),
        Text('$v', style: TextStyle(fontSize: 48, fontWeight: FontWeight.bold)),
        SizedBox(height: 8),
        Container(
          width: double.infinity,
          height: 24,
          decoration: BoxDecoration(border: Border.all(color: Colors.grey), borderRadius: BorderRadius.circular(6)),
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: pct,
            child: Container(decoration: BoxDecoration(color: Colors.blueAccent, borderRadius: BorderRadius.circular(6))),
          ),
        ),
        SizedBox(height: 12),
        _buildSparkline(),
      ],
    );
  }

  Widget _buildSparkline() {
    final data = widget.recent.map((e) => e.velocity.toDouble()).toList();
    if (data.isEmpty) return SizedBox(height: 40);
    final max = data.reduce((a, b) => a > b ? a : b);
    return SizedBox(
      height: 40,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: data.map((d) {
          final h = max == 0 ? 0.0 : (d / max) * 40.0;
          return Expanded(child: Container(margin: EdgeInsets.symmetric(horizontal: 1), height: h, color: Colors.greenAccent));
        }).toList(),
      ),
    );
  }
}
