import 'package:flutter/material.dart';

import 'models.dart';
import 'persistence.dart';

class PracticePlanConfigPage extends StatefulWidget {
  final PracticePlan? plan;
  PracticePlanConfigPage({this.plan});

  @override
  State<PracticePlanConfigPage> createState() => _PracticePlanConfigPageState();
}

class _PracticePlanConfigPageState extends State<PracticePlanConfigPage> {
  final _nameCtrl = TextEditingController();
  String _key = 'C';
  String _scale = 'major';
  int _octaves = 1;
  String _mode = 'constant';
  double _tempo = 60.0;
  int _accuracy = 80;

  late PracticePlan? _original;

  @override
  void initState() {
    super.initState();
    _original = widget.plan;
    if (_original != null) {
      _nameCtrl.text = _original!.name;
      _key = _original!.key;
      _scale = (_original!.scaleType == 'minor') ? '${_original!.minorVariant}_minor' : _original!.scaleType;
      _octaves = _original!.octaves;
      _mode = _original!.mode;
      _tempo = _original!.tempoBpm.toDouble();
      _accuracy = _original!.accuracyPercent;
    }
    _nameCtrl.addListener(() => setState(() {}));
  }

  bool get _isDirty {
    if (_original == null) {
      return _nameCtrl.text.trim().isNotEmpty || _tempo != 60.0 || _octaves != 1 || _key != 'C' || _scale != 'major' || _mode != 'constant' || _accuracy != 80;
    }
    return (_nameCtrl.text != _original!.name) || (_key != _original!.key) || (_scale != (_original!.scaleType == 'minor' ? '${_original!.minorVariant}_minor' : _original!.scaleType)) || (_octaves != _original!.octaves) || (_mode != _original!.mode) || (_tempo.toInt() != _original!.tempoBpm) || (_accuracy != _original!.accuracyPercent);
  }

  Future<void> _save() async {
    final plan = await _saveIntoPlan();
    Navigator.of(context).pop(plan);
  }

  Future<PracticePlan> _saveIntoPlan() async {
    final id = _original?.id ?? DateTime.now().millisecondsSinceEpoch.toString();
    String scaleType = _scale;
    String minorVariant = 'natural';
    if (_scale.endsWith('_minor')) {
      final parts = _scale.split('_');
      minorVariant = parts.first;
      scaleType = 'minor';
    }
    final plan = PracticePlan(
      id: id,
      name: _nameCtrl.text,
      mode: _mode,
      key: _key,
      scaleType: scaleType,
      minorVariant: minorVariant,
      octaves: _octaves,
      hand: 'HT',
      handSplit: HandSplit(strategy: 'automatic', splitMidiNote: 60),
      tempoBpm: _tempo.toInt(),
      accuracyPercent: _accuracy,
    );
    await savePracticePlan(plan);
    return plan;
  }

  void _revert() {
    // revert to original values (or defaults for new)
    if (_original != null) {
      _nameCtrl.text = _original!.name;
      _key = _original!.key;
      _scale = (_original!.scaleType == 'minor') ? '${_original!.minorVariant}_minor' : _original!.scaleType;
      _octaves = _original!.octaves;
      _mode = _original!.mode;
      _tempo = _original!.tempoBpm.toDouble();
      _accuracy = _original!.accuracyPercent;
    } else {
      _nameCtrl.text = '';
      _key = 'C';
      _scale = 'major';
      _octaves = 1;
      _mode = 'constant';
      _tempo = 60.0;
      _accuracy = 80;
    }
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
        appBar: AppBar(title: Text(widget.plan == null ? 'New Practice Plan' : 'Edit Practice Plan')),
        body: Padding(
          padding: const EdgeInsets.all(12.0),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
              TextField(controller: _nameCtrl, decoration: InputDecoration(labelText: 'Name')),
              SizedBox(height: 12),
              Row(children: [
                Expanded(child: DropdownButtonFormField<String>(initialValue: _key, items: ['C','D','E','F','G','A','B'].map((s)=>DropdownMenuItem(value:s,child:Text(s))).toList(), onChanged: (v){ if(v!=null)setState(()=>_key=v); })),
                SizedBox(width:8),
                Expanded(child: DropdownButtonFormField<String>(initialValue: _scale, items: ['major','natural_minor','harmonic_minor','melodic_minor'].map((s)=>DropdownMenuItem(value:s,child:Text(s))).toList(), onChanged: (v){ if(v!=null)setState(()=>_scale=v); })),
              ]),
              SizedBox(height:12),
              Row(children: [
                Text('Octaves'),
                SizedBox(width:8),
                DropdownButton<int>(value: _octaves, items: [1,2].map((n)=>DropdownMenuItem(value:n,child:Text('$n'))).toList(), onChanged:(v){ if(v!=null)setState(()=>_octaves=v); }),
                Spacer(),
                Text('Tempo'),
                SizedBox(width:8),
                SizedBox(width:80, child: TextFormField(initialValue: _tempo.toStringAsFixed(0), keyboardType: TextInputType.number, onChanged: (s){ final v=double.tryParse(s); if(v!=null)setState(()=>_tempo=v);})),
              ]),
              SizedBox(height:12),
              Row(children: [
                Expanded(child: ElevatedButton(onPressed: _isDirty ? _revert : null, child: Text('Revert Changes'))),
                SizedBox(width:8),
                ElevatedButton(onPressed: () async {
                  if (_isDirty) {
                    await _save();
                  } else {
                    Navigator.of(context).pop(_original);
                  }
                }, child: Text('Done')),
                SizedBox(width:8),
                ElevatedButton(onPressed: () async {
                  if (_isDirty) await _saveIntoPlan();
                  Navigator.of(context).popUntil((route) => route.isFirst);
                }, child: Text('Start Practice'))
              ]),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    // If there are unsaved changes when the page is disposed, save them.
    // This is fire-and-forget to avoid requiring an async dispose.
    if (_isDirty) {
      _saveIntoPlan();
    }
    _nameCtrl.dispose();
    super.dispose();
  }
}
