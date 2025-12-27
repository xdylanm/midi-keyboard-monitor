import 'package:flutter/material.dart';

import 'models.dart';
import 'persistence.dart';

class SettingsPage extends StatefulWidget {
  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  List<PracticePlan> _plans = [];
  GlobalConfig? _global;

  // simple form controllers
  final _nameCtrl = TextEditingController(text: 'New Plan');
  String _key = 'C';
  String _scale = 'major';
  int _octaves = 1;
  String _mode = 'constant';
  double _tempo = 60.0;
  int _accuracy = 80;

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    final plans = await loadAllPracticePlans();
    final g = await loadGlobalConfig();
    setState(() {
      _plans = plans;
      _global = g ?? GlobalConfig(version: '1.0', mapping: 'linear', calibration: Calibration(mode: 'none', min: 0.0, max: 1.0), autoBackupEnabled: true);
    });
  }

  Future<void> _savePlan() async {
    final id = DateTime.now().millisecondsSinceEpoch.toString();
    // Normalize scale selection: convert legacy minor variants to schema fields
    String scaleType = _scale;
    String minorVariant = 'natural';
    if (_scale.endsWith('_minor')) {
      final parts = _scale.split('_');
      minorVariant = parts.first;
      scaleType = 'minor';
    } else if (_scale == 'major') {
      scaleType = 'major';
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
    await _loadAll();
  }

  Future<void> _saveGlobal() async {
    if (_global == null) return;
    await saveGlobalConfig(_global!);
    await _loadAll();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Settings')),
      body: Padding(
        padding: const EdgeInsets.all(12.0),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Practice Plans', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              SizedBox(height: 8),
              for (var p in _plans)
                ListTile(
                  title: Text(p.name),
                  subtitle: Text('${p.scaleType} • ${p.octaves} octave(s) • ${p.tempoBpm} BPM'),
                  trailing: IconButton(
                    icon: Icon(Icons.delete),
                    onPressed: p.id == null ? null : () async {
                      await deletePracticePlan(p.id!);
                      await _loadAll();
                    },
                  ),
                ),
              Divider(),
              Text('Create New Plan', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
              TextField(controller: _nameCtrl, decoration: InputDecoration(labelText: 'Name')),
              Row(children: [
                Expanded(child: DropdownButtonFormField<String>(initialValue: _key, items: ['C','D','E','F','G','A','B'].map((s)=>DropdownMenuItem(value:s,child:Text(s))).toList(), onChanged: (v){ if(v!=null)setState(()=>_key=v); })),
                SizedBox(width:8),
                Expanded(child: DropdownButtonFormField<String>(initialValue: _scale, items: ['major','natural_minor','harmonic_minor','melodic_minor'].map((s)=>DropdownMenuItem(value:s,child:Text(s))).toList(), onChanged: (v){ if(v!=null)setState(()=>_scale=v); })),
              ]),
              Row(children: [
                Text('Octaves'),
                SizedBox(width:8),
                DropdownButton<int>(value: _octaves, items: [1,2].map((n)=>DropdownMenuItem(value:n,child:Text('$n'))).toList(), onChanged:(v){ if(v!=null)setState(()=>_octaves=v); }),
                Spacer(),
                Text('Tempo'),
                SizedBox(width:8),
                SizedBox(width:80, child: TextFormField(initialValue: _tempo.toStringAsFixed(0), keyboardType: TextInputType.number, onChanged: (s){ final v=double.tryParse(s); if(v!=null)setState(()=>_tempo=v);})),
              ]),
              SizedBox(height:8),
              ElevatedButton(onPressed: _savePlan, child: Text('Save Plan')),
              Divider(),
              Text('Global Config', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              SizedBox(height:8),
              if (_global != null) ...[
                DropdownButtonFormField<String>(initialValue: _global!.mapping, items: ['linear','square_root','logarithmic'].map((s)=>DropdownMenuItem(value:s,child:Text(s))).toList(), onChanged: (v){ if(v!=null) setState(()=> _global = GlobalConfig(version: _global!.version, mapping: v, calibration: _global!.calibration, autoBackupEnabled: _global!.autoBackupEnabled)); }),
                SizedBox(height:8),
                Text('Calibration Min: ${_global!.calibration.min.toStringAsFixed(2)}'),
                Slider(value: _global!.calibration.min, min:0, max:1, onChanged: (v){ setState(()=> _global = GlobalConfig(version: _global!.version, mapping: _global!.mapping, calibration: Calibration(mode: 'manual', min: v, max: _global!.calibration.max), autoBackupEnabled: _global!.autoBackupEnabled)); }),
                Text('Calibration Max: ${_global!.calibration.max.toStringAsFixed(2)}'),
                Slider(value: _global!.calibration.max, min:0, max:1, onChanged: (v){ setState(()=> _global = GlobalConfig(version: _global!.version, mapping: _global!.mapping, calibration: Calibration(mode: 'manual', min: _global!.calibration.min, max: v), autoBackupEnabled: _global!.autoBackupEnabled)); }),
                Row(children: [ElevatedButton(onPressed:_saveGlobal, child: Text('Save Global')), SizedBox(width:8), ElevatedButton(onPressed: () async { await saveGlobalConfig(GlobalConfig(version: '1.0', mapping: 'linear', calibration: Calibration(mode: 'none', min: 0.0, max: 1.0), autoBackupEnabled: true)); await _loadAll(); }, child: Text('Reset'))]),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
