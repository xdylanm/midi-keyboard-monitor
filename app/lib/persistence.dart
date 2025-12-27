import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'models.dart';

const _plansDirName = 'practice_plans';
const _globalConfigFile = 'global_config.json';

Future<Directory> _appDocsDir() async {
  if (_testAppDocsDir != null) return _testAppDocsDir!;
  final dir = await getApplicationDocumentsDirectory();
  return dir;
}

// Test hook: allow tests to override the app documents directory.
Directory? _testAppDocsDir;
void setAppDocsDirForTest(Directory d) {
  _testAppDocsDir = d;
}

Future<Directory> _plansDir() async {
  final base = await _appDocsDir();
  final d = Directory('${base.path}/$_plansDirName');
  if (!await d.exists()) await d.create(recursive: true);
  return d;
}

Future<File> savePracticePlan(PracticePlan plan) async {
  final dir = await _plansDir();
  final file = File('${dir.path}/${plan.id}.json');
  await file.writeAsString(jsonEncode(plan.toJson()));
  return file;
}

Future<List<PracticePlan>> loadAllPracticePlans() async {
  final dir = await _plansDir();
  final files = dir.listSync().whereType<File>().where((f) => f.path.endsWith('.json'));
  final out = <PracticePlan>[];
  for (var f in files) {
    try {
      final txt = await f.readAsString();
      final j = jsonDecode(txt) as Map<String, dynamic>;
      out.add(PracticePlan.fromJson(j));
    } catch (_) {}
  }
  return out;
}

Future<PracticePlan?> loadPracticePlanById(String id) async {
  final dir = await _plansDir();
  final file = File('${dir.path}/$id.json');
  if (!await file.exists()) return null;
  final txt = await file.readAsString();
  final j = jsonDecode(txt) as Map<String, dynamic>;
  return PracticePlan.fromJson(j);
}

Future<bool> deletePracticePlan(String id) async {
  final dir = await _plansDir();
  final file = File('${dir.path}/$id.json');
  if (await file.exists()) {
    await file.delete();
    return true;
  }
  return false;
}

Future<File> saveGlobalConfig(GlobalConfig cfg) async {
  final base = await _appDocsDir();
  final file = File('${base.path}/$_globalConfigFile');
  await file.writeAsString(jsonEncode(cfg.toJson()));
  return file;
}

Future<GlobalConfig?> loadGlobalConfig() async {
  final base = await _appDocsDir();
  final file = File('${base.path}/$_globalConfigFile');
  if (!await file.exists()) return null;
  try {
    final txt = await file.readAsString();
    final j = jsonDecode(txt) as Map<String, dynamic>;
    return GlobalConfig.fromJson(j);
  } catch (_) {
    return null;
  }
}

/// Export a plan to a file path suitable for sharing. Returns the File created.
Future<File?> exportPlanToFile(PracticePlan plan) async {
  final base = await _appDocsDir();
  final fname = '${plan.name.replaceAll(RegExp(r"[^a-zA-Z0-9_-]"), '_')}_${plan.id}.json';
  final file = File('${base.path}/$fname');
  try {
    await file.writeAsString(jsonEncode(plan.toJson()));
    return file;
  } catch (_) {
    return null;
  }
}

/// Import a plan from an arbitrary file path and save into the plans directory.
Future<PracticePlan?> importPlanFromFile(String path) async {
  final file = File(path);
  if (!await file.exists()) return null;
  try {
    final txt = await file.readAsString();
    final j = jsonDecode(txt) as Map<String, dynamic>;
    final plan = PracticePlan.fromJson(j);
    await savePracticePlan(plan);
    return plan;
  } catch (_) {
    return null;
  }
}
