import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

class SheetView extends StatefulWidget {
  const SheetView({Key? key}) : super(key: key);

  @override
  State<SheetView> createState() => _SheetViewState();
}

class _SheetViewState extends State<SheetView> {
  late final WebViewController _controller;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..loadHtmlString(_html);
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 240,
      child: Card(
        elevation: 2,
        child: Padding(
          padding: const EdgeInsets.all(8.0),
          child: WebViewWidget(controller: _controller),
        ),
      ),
    );
  }
}

const String _html = r'''
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/vexflow4@4.2.6/build/cjs/vexflow.min.js"></script>
    <style>body{margin:0;padding:0;}#score{padding:8px;}</style>
  </head>
  <body>
    <div id="score"></div>
    <script>
      (function(){
        const VF = Vex.Flow;
        const div = document.getElementById('score');
        const renderer = new VF.Renderer(div, VF.Renderer.Backends.SVG);
        renderer.resize(760, 220);
        const context = renderer.getContext();

        // Draw a single system with four measures (simple PoC of Mary Had a Little Lamb)
        const staveWidth = 170;
        const left = 10;
        const top = 20;

        const measures = [
          [ ['e/4','q'], ['d/4','q'], ['c/4','q'], ['d/4','q'] ],
          [ ['e/4','q'], ['e/4','q'], ['e/4','h'] ],
          [ ['d/4','q'], ['d/4','q'], ['d/4','h'] ],
          [ ['e/4','q'], ['g/4','q'], ['g/4','h'] ]
        ];

        for (let i=0;i<measures.length;i++){
          const x = left + i*staveWidth;

          const stave = new VF.Stave(x, top, staveWidth-10);
          if (i===0) {
            stave.addClef('treble').addTimeSignature('4/4');
          }
          stave.setContext(context).draw();

          const notes = measures[i].map(n => {
            return new VF.StaveNote({keys:[n[0]], duration:n[1]});
          });

          const voice = new VF.Voice({num_beats:4, beat_value:4});
          voice.addTickables(notes);
          new VF.Formatter().joinVoices([voice]).format([voice], stave.getWidth()-20);
          voice.draw(context, stave);
        }
      })();
    </script>
  </body>
</html>
''';
