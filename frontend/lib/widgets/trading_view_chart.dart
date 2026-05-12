import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

class TradingViewChart extends StatefulWidget {
  final String ticker;
  const TradingViewChart({super.key, required this.ticker});

  @override
  State<TradingViewChart> createState() => _TradingViewChartState();
}

class _TradingViewChartState extends State<TradingViewChart> {
  late final WebViewController _controller;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0x00000000))
      ..loadHtmlString(_getHtmlContent());
  }

  String _getHtmlContent() {
    return '''
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
      <style>
        body { margin: 0; padding: 0; background-color: #121212; }
        #chart { width: 100vw; height: 100vh; }
      </style>
    </head>
    <body>
      <div id="chart"></div>
      <script>
        const chartOptions = { 
          layout: { background: { type: 'solid', color: '#121212' }, textColor: '#d1d4dc' },
          grid: { vertLines: { color: 'rgba(42, 46, 57, 0.5)' }, horzLines: { color: 'rgba(42, 46, 57, 0.5)' } },
          rightPriceScale: { borderVisible: false },
          timeScale: { borderVisible: false },
        };
        const chart = LightweightCharts.createChart(document.getElementById('chart'), chartOptions);
        const candleSeries = chart.addCandlestickSeries({
          upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
          wickUpColor: '#26a69a', wickDownColor: '#ef5350',
        });

        // Simular datos o cargar vía API (aquí cargamos una demo)
        const data = [
          { time: '2023-12-22', open: 150.00, high: 155.00, low: 148.00, close: 153.00 },
          { time: '2023-12-23', open: 153.00, high: 158.00, low: 152.00, close: 157.00 },
          { time: '2023-12-24', open: 157.00, high: 160.00, low: 155.00, close: 159.00 },
          { time: '2023-12-25', open: 159.00, high: 162.00, low: 158.00, close: 161.00 },
        ];
        candleSeries.setData(data);

        window.addEventListener('resize', () => {
          chart.resize(window.innerWidth, window.innerHeight);
        });
      </script>
    </body>
    </html>
    ''';
  }

  @override
  Widget build(BuildContext context) {
    return WebViewWidget(controller: _controller);
  }
}
