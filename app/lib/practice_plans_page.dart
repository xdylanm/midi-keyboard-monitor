import 'package:flutter/material.dart';

import 'models.dart';
import 'persistence.dart';
import 'practice_plan_config_page.dart';

class PracticePlansPage extends StatefulWidget {
  @override
  State<PracticePlansPage> createState() => _PracticePlansPageState();
}

class _PracticePlansPageState extends State<PracticePlansPage> {
  List<PracticePlan> _plans = [];
  List<PracticePlan> _visible = [];
  String _query = '';
  final TextEditingController _searchCtrl = TextEditingController();

  // no form on this page; config lives on a separate screen

  @override
  void initState() {
    super.initState();
    _loadPlans();
  }

  Future<void> _loadPlans() async {
    final plans = await loadAllPracticePlans();
    // Sort by id timestamp descending (newest first) when possible
    plans.sort((a, b) {
      try {
        final ai = int.tryParse(a.id ?? '') ?? 0;
        final bi = int.tryParse(b.id ?? '') ?? 0;
        return bi.compareTo(ai);
      } catch (_) {
        return 0;
      }
    });
    setState(() {
      _plans = plans;
      _applyFilter();
    });
  }

  void _applyFilter() {
    final q = _query.trim();
    // reset debug parts
    if (q.isEmpty) {
      _visible = List.from(_plans);
      return;
    }

    // check for starting with a single key character (A-G)
    String? keyPart;
    String? scalePart;
    final keyScaleMatch = RegExp(r'^([A-Ga-g][#b]?)(?:\s+([a-z]+))?', caseSensitive: false).firstMatch(q);
    if (q.length < 2 && keyScaleMatch == null) {
      _visible = List.from(_plans);
      return;
    }

    if (keyScaleMatch != null) {
      keyPart = keyScaleMatch.group(1)?.toUpperCase();
      scalePart = keyScaleMatch.group(2)?.toLowerCase();
    }

    int? bpm;
    final nm = RegExp(r'^(\d{1,3})(?:\s*bpm)?', caseSensitive: false).firstMatch(q);
    if (nm != null) {
      bpm = int.tryParse(nm.group(1)!);
    }

    final lower = q.toLowerCase();

    _visible = _plans.where((p) {
      // name exact/substring or fuzzy match
      if (p.name.toLowerCase().contains(lower) || _fuzzyMatch(p.name, q)) {
        return true;
      } 

      // bpm match
      if (bpm != null) {
        if ((p.tempoBpm - bpm).abs() <= 8) {
          return true;
        }
      }

      // key+scale match
      if (keyPart != null) {
        final planKey = p.key.toUpperCase();
        if (planKey == keyPart) {
          if (scalePart == null) return true;
          // accept abbreviations/prefixes like 'ma'/'maj' -> major, 'mi'/'min' -> minor
          final sp = scalePart.toLowerCase();
          if (p.scaleType.toLowerCase().startsWith(sp)) return true;
        }
        // if a root key was specified but didn't match this plan, don't match on scale-only fallback
        return false;
      }

      // fallback: substring in key/scale or tempo text (only when no explicit root was specified)
      if (p.scaleType.toLowerCase().startsWith(lower)) return true;
      
      return false;
    }).toList();
  }

  // Normalize a string for fuzzy comparison (lowercase, strip punctuation)
  String _normalize(String s) => s.toLowerCase().replaceAll(RegExp(r"[^a-z0-9#b\s]"), ' ').replaceAll(RegExp(r'\s+'), ' ').trim();

  // Levenshtein distance
  int _levenshtein(String a, String b) {
    final la = a.length;
    final lb = b.length;
    if (la == 0) return lb;
    if (lb == 0) return la;
    List<int> v0 = List<int>.generate(lb + 1, (i) => i);
    List<int> v1 = List<int>.filled(lb + 1, 0);
    for (var i = 0; i < la; i++) {
      v1[0] = i + 1;
      for (var j = 0; j < lb; j++) {
        final cost = a[i] == b[j] ? 0 : 1;
        v1[j + 1] = [v1[j] + 1, v0[j + 1] + 1, v0[j] + cost].reduce((x, y) => x < y ? x : y);
      }
      final tmp = v0;
      v0 = v1;
      v1 = tmp;
    }
    return v0[lb];
  }

  // Fuzzy match a plan name against a short query using token-level Levenshtein
  bool _fuzzyMatch(String name, String query) {
    final n = _normalize(name);
    final q = _normalize(query);
    // exact substring still wins
    if (n.contains(q)) return true;

    // make fuzzy matching stricter: require at least 3 characters in the
    // overall query and in each token to perform fuzzy comparisons. This
    // prevents very short queries like "G ma" from matching unrelated names.
    if (q.length < 3) return false;

    final nTokens = n.split(' ').where((t) => t.isNotEmpty).toList();
    final qTokens = q.split(' ').where((t) => t.isNotEmpty).toList();

    for (var qt in qTokens) {
      if (qt.length < 3) continue; // skip short query tokens
      for (var nt in nTokens) {
        if (nt.contains(qt)) return true; // substring match for longer tokens
        // tighter threshold: allow 1 edit for very short tokens, otherwise ~length/4
        final thresh = qt.length <= 4 ? 1 : (qt.length / 4).ceil();
        final d = _levenshtein(qt, nt);
        if (d <= thresh) return true;
      }
    }

    // full-string compare with a conservative threshold
    final fullThresh = q.length <= 4 ? 1 : (q.length / 4).ceil();
    if (_levenshtein(q, n) <= fullThresh) return true;
    return false;
  }

  // navigation helpers: open config page for creating or editing a plan
  Future<void> _openConfigForNew() async {
    final result = await Navigator.of(context).push(MaterialPageRoute(builder: (_) => PracticePlanConfigPage()));
    if (result is PracticePlan) await _loadPlans();
  }

  Future<void> _openConfigForPlan(PracticePlan p) async {
    final result = await Navigator.of(context).push(MaterialPageRoute(builder: (_) => PracticePlanConfigPage(plan: p)));
    if (result is PracticePlan) await _loadPlans();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Practice Plans')),
      body: Padding(
        padding: const EdgeInsets.all(12.0),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // search field (always visible)
              TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  hintText: 'Search plans (name, key, tempo)',
                  suffixIcon: _query.isNotEmpty
                      ? IconButton(icon: Icon(Icons.clear), onPressed: () { _searchCtrl.clear(); setState(() { _query = ''; _applyFilter(); }); })
                      : null,
                ),
                onChanged: (s) {
                  setState(() {
                    _query = s;
                    _applyFilter();
                  });
                },
              ),
              SizedBox(height: 8),
              // create new at top (always shown)
              ListTile(
                leading: Icon(Icons.add),
                title: Text('Create New Plan'),
                onTap: _openConfigForNew,
              ),
              Divider(),
              // if query active, show filtered list, else show full list
              if (_visible.isEmpty && _query.trim().length >= 1)
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Text('No results found'),
                ),
              ...(_query.trim().length >= 1 ? _visible : _plans).map((p) => ListTile(
                    title: Text(p.name),
                    subtitle: Text('${p.key} ${p.scaleType} • ${p.octaves} octave(s) • ${p.tempoBpm} BPM'),
                    onTap: () => _openConfigForPlan(p),
                    trailing: IconButton(
                      icon: Icon(Icons.delete),
                      onPressed: p.id == null
                          ? null
                          : () async {
                              final ok = await showDialog<bool>(
                                context: context,
                                builder: (context) => AlertDialog(
                                  title: Text('Delete "${p.name}"?'),
                                  content: Text('This will permanently delete the practice plan.'),
                                  actions: [
                                    TextButton(onPressed: () => Navigator.of(context).pop(false), child: Text('Cancel')),
                                    TextButton(onPressed: () => Navigator.of(context).pop(true), child: Text('Delete')),
                                  ],
                                ),
                              );
                              if (ok == true) {
                                await deletePracticePlan(p.id!);
                                await _loadPlans();
                              }
                            },
                    ),
                  )),
            ],
          ),
        ),
      ),
    );
  }
}


