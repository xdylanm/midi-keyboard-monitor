import 'package:flutter/material.dart';

import 'models.dart';
import 'persistence.dart';

class SettingsPage extends StatefulWidget {
  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  GlobalConfig? _global;


  @override
  void initState() {
    super.initState();
    _loadGlobal();
  }
  Future<void> _saveGlobal() async {
    if (_global == null) return;
    await saveGlobalConfig(_global!);
    await _loadGlobal();
  }

  Future<void> _loadGlobal() async {
    final g = await loadGlobalConfig();
    setState(() {
      _global = g ?? GlobalConfig(version: '1.0', mapping: 'linear', calibration: Calibration(mode: 'none', min: 0.0, max: 1.0), autoBackupEnabled: true);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('App Settings')),
      body: Padding(
        padding: const EdgeInsets.all(12.0),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Global Config', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              SizedBox(height:8),
              if (_global != null) ...[
                DropdownButtonFormField<String>(initialValue: _global!.mapping, items: ['linear','square_root','logarithmic'].map((s)=>DropdownMenuItem(value:s,child:Text(s))).toList(), onChanged: (v){ if(v!=null) setState(()=> _global = GlobalConfig(version: _global!.version, mapping: v, calibration: _global!.calibration, autoBackupEnabled: _global!.autoBackupEnabled)); }),
                SizedBox(height:8),
                Text('Calibration Min: ${_global!.calibration.min.toStringAsFixed(2)}'),
                Slider(value: _global!.calibration.min, min:0, max:1, onChanged: (v){ setState(()=> _global = GlobalConfig(version: _global!.version, mapping: _global!.mapping, calibration: Calibration(mode: 'manual', min: v, max: _global!.calibration.max), autoBackupEnabled: _global!.autoBackupEnabled)); }),
                Text('Calibration Max: ${_global!.calibration.max.toStringAsFixed(2)}'),
                Slider(value: _global!.calibration.max, min:0, max:1, onChanged: (v){ setState(()=> _global = GlobalConfig(version: _global!.version, mapping: _global!.mapping, calibration: Calibration(mode: 'manual', min: _global!.calibration.min, max: v), autoBackupEnabled: _global!.autoBackupEnabled)); }),
                Row(children: [ElevatedButton(onPressed:_saveGlobal, child: Text('Save Global')), SizedBox(width:8), ElevatedButton(onPressed: () async { await saveGlobalConfig(GlobalConfig(version: '1.0', mapping: 'linear', calibration: Calibration(mode: 'none', min: 0.0, max: 1.0), autoBackupEnabled: true)); await _loadGlobal(); }, child: Text('Reset'))]),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
