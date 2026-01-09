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
  final _keyCtrl = TextEditingController();
  String _key = 'C';
  bool _keyValid = true;
  bool _showSharps = true;
  String _scale = 'major';
  int _octaves = 1;
  String _mode = 'constant';
  double _tempo = 60.0;
  int _accuracy = 80;
  String _hand = 'HT';
  String _chordMode = 'mean';
  List<ConstantTarget> _constantTargets = [];
  List<VariableTarget> _variableTargets = [];
  String _constantIntensity = 'mf';
  String _varStart = 'mp';
  String _varEnd = 'mf';
  String _varDirection = 'crescendo';

  late PracticePlan? _original;

  @override
  void initState() {
    super.initState();
    _original = widget.plan;
    if (_original != null) {
      _nameCtrl.text = _original!.name;
      _key = _original!.key;
      _keyCtrl.text = _key;
      _scale = (_original!.scaleType == 'minor') ? '${_original!.minorVariant}_minor' : _original!.scaleType;
      _octaves = _original!.octaves;
      _mode = _original!.mode;
      _tempo = _original!.tempoBpm.toDouble();
      _accuracy = _original!.accuracyPercent;
      _hand = _original!.hand;
      _chordMode = _original!.chordMode;
      _constantTargets = _original!.constantTargets ?? [];
      if (_constantTargets.isNotEmpty) _constantIntensity = _constantTargets[0].intensityLabel;
      _variableTargets = _original!.variableTargets ?? [];
      if (_variableTargets.isNotEmpty) {
        final v = _variableTargets[0];
        _varStart = v.startIntensity;
        _varEnd = v.endIntensity;
        _varDirection = v.direction ?? _varDirection;
      }
      // Ensure at least one target exists for each type
      if (_constantTargets.isEmpty) {
        _constantTargets = [ConstantTarget(intensityLabel: _constantIntensity)];
      }
      if (_variableTargets.isEmpty) {
        _variableTargets = [VariableTarget(startIntensity: _varStart, endIntensity: _varEnd, direction: _varDirection)];
      }
      
    }
    _nameCtrl.addListener(() => setState(() {}));
    _keyCtrl.addListener(() {
      final raw = _keyCtrl.text;
      final nk = normalizeKey(raw);
      setState(() {
        // If the user typed a flat (e.g. Db or D♭) while in sharps mode,
        // switch the display to flats so UI reflects their input.
        final flatInput = RegExp(r'^[A-Ga-g](?:b|♭)$');
        if (_showSharps && flatInput.hasMatch(raw.trim())) {
          _showSharps = false;
        }
        _keyValid = nk != null;
        if (nk != null) _key = nk;
      });
    });
  }

  bool get _isDirty {
    if (_original == null) {
      return _nameCtrl.text.trim().isNotEmpty || _tempo != 60.0 || _octaves != 1 || _key != 'C' || _scale != 'major' || _mode != 'constant' || _accuracy != 80 || _hand != 'HT' || _chordMode != 'mean';
    }
    return (_nameCtrl.text != _original!.name)
      || (_key != _original!.key)
      || (_scale != (_original!.scaleType == 'minor' ? '${_original!.minorVariant}_minor' : _original!.scaleType))
      || (_octaves != _original!.octaves)
      || (_mode != _original!.mode)
      || (_tempo.toInt() != _original!.tempoBpm)
      || (_accuracy != _original!.accuracyPercent)
        || (_hand != _original!.hand)
        || (_chordMode != _original!.chordMode);
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
      hand: _hand,
      tempoBpm: _tempo.toInt(),
      accuracyPercent: _accuracy,
      chordMode: _chordMode,
      constantTargets: _constantTargets,
      variableTargets: _variableTargets,
      
    );
    await savePracticePlan(plan);
    return plan;
  }

  void _revert() {
    // revert to original values (or defaults for new)
    if (_original != null) {
      _nameCtrl.text = _original!.name;
      _key = _original!.key;
      _keyCtrl.text = _key;
      _scale = (_original!.scaleType == 'minor') ? '${_original!.minorVariant}_minor' : _original!.scaleType;
      _octaves = _original!.octaves;
      _mode = _original!.mode;
      _tempo = _original!.tempoBpm.toDouble();
      _accuracy = _original!.accuracyPercent;
      _hand = _original!.hand;
      _chordMode = _original!.chordMode;
      _constantTargets = _original!.constantTargets ?? [ConstantTarget(intensityLabel: _constantIntensity)];
      _variableTargets = _original!.variableTargets ?? [VariableTarget(startIntensity: _varStart, endIntensity: _varEnd, direction: _varDirection)];
    } else {
      _nameCtrl.text = '';
      _key = 'C';
      _keyCtrl.text = _key;
      _scale = 'major';
      _octaves = 1;
      _mode = 'constant';
      _tempo = 60.0;
      _accuracy = 80;
      _hand = 'HT';
      _chordMode = 'mean';
      _constantTargets = [ConstantTarget(intensityLabel: _constantIntensity)];
      _variableTargets = [VariableTarget(startIntensity: _varStart, endIntensity: _varEnd, direction: _varDirection)];
    }
    setState(() {});
  }

  String? normalizeKey(String s) {
    final inS = s.trim().toUpperCase();
    if (inS.isEmpty) return null;
    final normalized = inS.replaceAll('♯', '#').replaceAll('♭', 'B');
    final regex = RegExp(r'^[A-G](?:#|B)?$');
    if (!regex.hasMatch(normalized)) return null;
    // canonical mapping: prefer sharps for enharmonics
    final map = {
      'DB': 'C#', 'EB': 'D#', 'E#': 'F', 'FB': 'E', 'CB': 'B', 'B#': 'C', 'GB': 'F#', 'AB': 'G#', 'BB': 'A#'
    };
    if (map.containsKey(normalized)) return map[normalized]!;
    return normalized;
  }

  String get displayScaleLabel {
    if (_scale == 'major') return 'Major';
    if (_scale.endsWith('_minor')) {
      final parts = _scale.split('_');
      final v = parts.first;
      return 'Minor (${v[0].toUpperCase()}${v.substring(1)})';
    }
    return _scale;
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
              // Key and scale
              Row(children: [
                Expanded(child: TextField(
                  controller: _keyCtrl, 
                  decoration: InputDecoration(
                    labelText: 'Root Key', 
                    hintText: 'C, C#, Db, F♯', 
                    errorText: _keyValid ? null : 'Invalid key (A-G plus optional # or b)'))),
                SizedBox(width:8),
                Expanded(child: DropdownButtonFormField<String>(
                  initialValue: _scale, 
                  items: [
                    DropdownMenuItem(value: 'major', child: Text('Major')),
                    DropdownMenuItem(value: 'natural_minor', child: Text('Minor (Natural)')),
                    DropdownMenuItem(value: 'harmonic_minor', child: Text('Minor (Harmonic)')),
                    DropdownMenuItem(value: 'melodic_minor', child: Text('Minor (Melodic)')),
                  ], 
                  decoration: InputDecoration(labelText: 'Scale Type'),
                  onChanged: (v){ if(v!=null) setState(()=>_scale=v); })),
              ]),
              SizedBox(height:12),
              Row(children: [
                Text('Octaves'),
                SizedBox(width:8),
                DropdownButton<int>(value: _octaves, items: [1,2].map((n)=>DropdownMenuItem(value:n,child:Text('$n'))).toList(), onChanged:(v){ if(v!=null)setState(()=>_octaves=v); }),
                SizedBox(width:16),
                Text('Tempo'),
                SizedBox(width:8),
                Expanded(child: TextFormField(
                  initialValue: _tempo.toStringAsFixed(0), 
                  keyboardType: TextInputType.number, 
                  onChanged: (s){ final v=double.tryParse(s); if(v!=null)setState(()=>_tempo=v);})),
              ]),
              SizedBox(height:8),
              Row(children: [
                Expanded(child: DropdownButtonFormField<String>(
                  initialValue: _hand,
                  items: [
                    DropdownMenuItem(value: 'LH', child: Text('Left')), 
                    DropdownMenuItem(value: 'RH', child: Text('Right')), 
                    DropdownMenuItem(value: 'HT', child: Text('Together'))], 
                  onChanged: (v){ if(v!=null)setState(()=>_hand=v); },
                  decoration: InputDecoration(labelText: 'Hands'),
                )),
                SizedBox(width:8),
                Expanded(child: DropdownButtonFormField<String>(
                  initialValue: _chordMode,
                  items: [
                    DropdownMenuItem(value: 'mean', child: Text('Average')), 
                    DropdownMenuItem(value: 'per-voice', child: Text('Per Voice'))],
                  decoration: InputDecoration(labelText: 'Chord Accuracy Mode'),
                  onChanged: (v){ if(v!=null)setState(()=>_chordMode=v); }
                )),
              ]),
              SizedBox(height:12),
              Row(children: [
                Expanded(child: InputDecorator(
                  decoration: InputDecoration(labelText: 'Accuracy Tolerance'),
                  child: Slider(
                    value: _accuracy.toDouble(),
                    min: 10,
                    max: 100,
                    divisions: 18,
                    label: '$_accuracy%',
                    onChanged: (v) { setState(() => _accuracy = v.toInt()); },
                  ),
                )),
              ]),
              SizedBox(height:12),
              // Practice mode
              Row(children: [
                Text('Practice mode'),
                SizedBox(width:8),
                ChoiceChip(label: Text('Constant'), selected: _mode=='constant', onSelected: (v){ if (v) setState(()=>_mode='constant'); }),
                SizedBox(width:8),
                ChoiceChip(label: Text('Variable'), selected: _mode=='variable', onSelected: (v){ if (v) setState(()=>_mode='variable'); }),
              ]),
              SizedBox(height:12),
              // Targets (single constant + single variable)
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Constant Target'),
                SizedBox(height:8),
                Row(children: [
                  Expanded(
                    child: InputDecorator(
                      decoration: InputDecoration(labelText: 'Intensity'), 
                      child: DropdownButton<String>(
                        isExpanded: true,
                        value: _constantTargets.isNotEmpty ? _constantTargets[0].intensityLabel : _constantIntensity,
                        items: ['pp','p','mp','mf','f','ff'].map((s)=>DropdownMenuItem(value:s,child:Text(s, overflow: TextOverflow.ellipsis, maxLines: 1))).toList(),
                        onChanged: (v){ if(v!=null) setState((){ if (_constantTargets.isEmpty) { _constantTargets = [ConstantTarget(intensityLabel: v)]; } else { _constantTargets[0] = ConstantTarget(intensityLabel: v); } _constantIntensity = v; }); }
                      ),
                    ),
                  ),
                ],),
                SizedBox(height:12),
                Text('Variable Target'),
                SizedBox(height:8),
                Row(children: [
                  Expanded(
                    child: InputDecorator(
                      decoration:  InputDecoration(labelText: 'Start'), 
                      child: DropdownButton<String>(
                        isExpanded: true,
                        value: _variableTargets.isNotEmpty ? _variableTargets[0].startIntensity : _varStart,
                        items: ['pp','p','mp','mf','f','ff'].map((s)=>DropdownMenuItem(value:s,child:Text(s, overflow: TextOverflow.ellipsis, maxLines: 1))).toList(),
                        onChanged: (v){ if(v!=null) setState((){ _varStart = v; if (_variableTargets.isEmpty) { _variableTargets = [VariableTarget(startIntensity: _varStart, endIntensity: _varEnd, direction: _varDirection)]; } else { _variableTargets[0] = VariableTarget(startIntensity: _varStart, endIntensity: _varEnd, direction: _varDirection); } }); }
                      ),
                    ),
                  ),
                  SizedBox(width:12),
                  Expanded(
                    child: InputDecorator(
                      decoration:  InputDecoration(labelText: 'End'),
                      child: DropdownButton<String>(
                        isExpanded: true,
                        value: _variableTargets.isNotEmpty ? _variableTargets[0].endIntensity : _varEnd,
                        items: ['pp','p','mp','mf','f','ff'].map((s)=>DropdownMenuItem(value:s,child:Text(s, overflow: TextOverflow.ellipsis, maxLines: 1))).toList(),
                        onChanged: (v){ if(v!=null) setState((){ _varEnd = v; if (_variableTargets.isEmpty) { _variableTargets = [VariableTarget(startIntensity: _varStart, endIntensity: _varEnd, direction: _varDirection)]; } else { _variableTargets[0] = VariableTarget(startIntensity: _varStart, endIntensity: _varEnd, direction: _varDirection); } }); }
                      ),
                    ),
                  ),
                  SizedBox(width:12),
                  Expanded(flex:2,
                    child: InputDecorator(
                      decoration:  InputDecoration(labelText: 'Dynamic'),
                      child: DropdownButton<String>(
                        isExpanded: true,
                        value: _variableTargets.isNotEmpty ? _variableTargets[0].direction : _varDirection,
                        items: ['crescendo','decrescendo'].map((s)=>DropdownMenuItem(value:s,child:Text(s, overflow: TextOverflow.ellipsis, maxLines: 1))).toList(),
                        onChanged: (v){ if(v!=null) setState((){ _varDirection = v; if (_variableTargets.isEmpty) { _variableTargets = [VariableTarget(startIntensity: _varStart, endIntensity: _varEnd, direction: _varDirection)]; } else { _variableTargets[0] = VariableTarget(startIntensity: _varStart, endIntensity: _varEnd, direction: _varDirection); } }); }
                      ),
                    ),
                  ),
                  Spacer()
                ]),
              ]),
              SizedBox(height:12),
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
    _keyCtrl.dispose();
    super.dispose();
  }
}
