import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:candlesticks/candlesticks.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:provider/provider.dart';
import '../config/api_config.dart';
import '../core/app_state.dart';
import '../widgets/trading_view_chart.dart';
import '../widgets/order_book.dart';
import '../widgets/price_ticker.dart';

class StockDetailScreen extends StatefulWidget {
  final String ticker;
  const StockDetailScreen({super.key, required this.ticker});

  @override
  State<StockDetailScreen> createState() => _StockDetailScreenState();
}

class _StockDetailScreenState extends State<StockDetailScreen> {
  bool isLoading = true;
  String _selectedPeriod = '1mo';
  Map<String, dynamic>? data;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData([String? period]) async {
    final p = period ?? _selectedPeriod;
    if (mounted) {
      setState(() {
        isLoading = true;
        _selectedPeriod = p;
      });
    }
    try {
      final response = await http.get(
        ApiConfig.buildUri('/predict/${widget.ticker}', {'period': p}),
      );
      if (response.statusCode == 200 && mounted) {
        setState(() {
          data = json.decode(response.body);
          isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).cardColor,
        elevation: 0,
        iconTheme: IconThemeData(
          color: Theme.of(context).textTheme.bodyLarge?.color,
        ),
        title: Text(
          widget.ticker,
          style: TextStyle(color: Theme.of(context).textTheme.bodyLarge?.color),
        ),
        actions: [
          Consumer<AppState>(
            builder: (context, appState, _) {
              final isFav = appState.watchlist.any(
                (s) =>
                    s['ticker'].toString().toUpperCase() ==
                    widget.ticker.toUpperCase(),
              );
              return IconButton(
                icon: Icon(
                  isFav ? Icons.star : Icons.star_border,
                  color: isFav ? Colors.amber : Colors.grey,
                ),
                onPressed: () async {
                  final success = await appState.toggleWatchlist(widget.ticker);
                  if (!success && context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Error al actualizar favoritos'),
                        backgroundColor: Colors.red,
                      ),
                    );
                  }
                },
              );
            },
          ),
        ],
      ),
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : data == null
          ? const Center(child: Text("No se pudo cargar la información"))
          : _buildDetailContent(),
    );
  }

  Widget _buildDetailContent() {
    final bool isPro = Provider.of<AppState>(context).isProMode;

    return SingleChildScrollView(
      padding: EdgeInsets.all(isPro ? 10 : 25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeaderCard(isPro),
          if (isPro) ...[
            const SizedBox(height: 20),
            OrderBook(
              basePrice: (data!['precio'] ?? data!['price'] ?? 0.0).toDouble(),
            ),
          ],
          const SizedBox(height: 25),
          Text(
            "AI Analysis",
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 15),
          _buildAIRecommendationCard(),
          const SizedBox(height: 40),
          _buildDecisionButtons(),
        ],
      ),
    );
  }

  Widget _buildHeaderCard(bool isPro) {
    var priceValue = (data!['precio'] ?? data!['price'] ?? 0.0);
    double price = priceValue is String
        ? double.parse(priceValue)
        : (priceValue as num).toDouble();

    final List ohlcRaw = data!['ohlc'] is List ? data!['ohlc'] : [];
    final List<Candle> candles = [];

    for (var e in ohlcRaw) {
      try {
        candles.add(
          Candle(
            date: DateTime.parse(e['date']),
            high: (e['high'] as num).toDouble(),
            low: (e['low'] as num).toDouble(),
            open: (e['open'] as num).toDouble(),
            close: (e['close'] as num).toDouble(),
            volume: (e['volume'] as num).toDouble(),
          ),
        );
      } catch (err) {
        debugPrint("Error parsing candle: $err");
      }
    }

    final List<Candle> processedCandles = candles.reversed.toList();

    return Container(
      padding: EdgeInsets.all(isPro ? 10 : 25),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(25),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                widget.ticker,
                style: GoogleFonts.poppins(
                  fontSize: isPro ? 24 : 35,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              PriceTicker(
                price: price,
                fontSize: isPro ? 20 : 28,
                color: Colors.lightBlueAccent,
              ),
            ],
          ),
          const SizedBox(height: 15),
          _buildTimeframeSelector(),
          const SizedBox(height: 15),
          SizedBox(
            height: isPro ? 450 : 350,
            child: isPro
                ? TradingViewChart(ticker: widget.ticker)
                : processedCandles.length >= 2
                ? Theme(
                    data: ThemeData.dark(),
                    child: Candlesticks(
                      key: ValueKey("${widget.ticker}_$_selectedPeriod"),
                      candles: processedCandles,
                    ),
                  )
                : const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.show_chart, size: 50, color: Colors.grey),
                        SizedBox(height: 10),
                        Text(
                          "Datos insuficientes para el gráfico",
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimeframeSelector() {
    final periods = [
      {'label': '1D', 'value': '1d'},
      {'label': '5D', 'value': '5d'},
      {'label': '15D', 'value': '15d'},
      {'label': '1M', 'value': '1mo'},
      {'label': '6M', 'value': '6mo'},
      {'label': '1A', 'value': '1y'},
    ];

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: periods.map((p) {
          final isSelected = _selectedPeriod == p['value'];
          return Padding(
            padding: const EdgeInsets.only(right: 8.0),
            child: ChoiceChip(
              label: Text(
                p['label']!,
                style: GoogleFonts.poppins(
                  fontSize: 12,
                  color: isSelected ? Colors.white : Colors.grey,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
              selected: isSelected,
              onSelected: (selected) {
                if (selected) _fetchData(p['value']);
              },
              selectedColor: Colors.lightBlueAccent,
              backgroundColor: const Color(0xFF2A2A2A),
              checkmarkColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 4),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildAIRecommendationCard() {
    final String rawRec = (data!['recomendacion'] ?? 'esperar')
        .toString()
        .toLowerCase();

    bool isBuy = rawRec.contains("comprar");

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isBuy
            ? const Color(0xFF1B5E20).withValues(alpha: 0.2)
            : const Color(0xFFBF360C).withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isBuy
              ? Colors.greenAccent.withValues(alpha: 0.3)
              : Colors.redAccent.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.auto_awesome,
            color: isBuy ? Colors.greenAccent : Colors.redAccent,
          ),
          const SizedBox(width: 15),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "ANÁLISIS DE IA",
                  style: GoogleFonts.poppins(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: Colors.grey[400],
                  ),
                ),
                Text(
                  rawRec.toUpperCase(),
                  style: GoogleFonts.poppins(
                    fontWeight: FontWeight.bold,
                    fontSize: 18,
                    color: isBuy ? Colors.greenAccent : Colors.redAccent,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDecisionButtons() {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: () => _handleDecision("no compré"),
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: Colors.white24),
              foregroundColor: Colors.white70,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: const Text("No comprar"),
          ),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: ElevatedButton(
            onPressed: _showBuyDialog,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.lightBlueAccent,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: const Text("Comprar"),
          ),
        ),
      ],
    );
  }

  Future<void> _handleDecision(String decision) async {
    try {
      await http.post(
        ApiConfig.buildUri('/decision'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'ticker': widget.ticker, 'decision': decision}),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Decisión registrada: $decision'),
            backgroundColor: Colors.lightBlueAccent,
          ),
        );
      }
    } catch (e) {
      debugPrint("Error saving decision: $e");
    }
  }

  void _showBuyDialog() {
    final TextEditingController qtyController = TextEditingController(
      text: "1",
    );
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Comprar ${widget.ticker}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              "Precio actual: \$${(data!['precio'] ?? 0.0).toStringAsFixed(2)}",
            ),
            const SizedBox(height: 15),
            TextField(
              controller: qtyController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: "Cantidad de acciones",
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: () {
              final int? qty = int.tryParse(qtyController.text);
              if (qty != null && qty > 0) {
                _executeTrade(qty);
                Navigator.pop(context);
              }
            },
            child: const Text('Comprar ahora'),
          ),
        ],
      ),
    );
  }

  Future<void> _executeTrade(int quantity) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');

    if (token == null) return;

    try {
      final response = await http.post(
        ApiConfig.buildUri('/trade/buy', {'ticker': widget.ticker, 'quantity': quantity.toString()}),
        headers: {'Authorization': 'Bearer $token'},
      );

      final resData = json.decode(response.body);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(resData['message']),
            backgroundColor: resData['status'] == 'success'
                ? Colors.green
                : Colors.red,
          ),
        );
        if (resData['status'] == 'success') {
          _handleDecision("compré");
        }
      }
    } catch (e) {
      debugPrint("Error executing trade: $e");
    }
  }
}