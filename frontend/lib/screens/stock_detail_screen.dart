import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:candlesticks/candlesticks.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';

class StockDetailScreen extends StatefulWidget {
  final String ticker;
  const StockDetailScreen({super.key, required this.ticker});

  @override
  _StockDetailScreenState createState() => _StockDetailScreenState();
}

class _StockDetailScreenState extends State<StockDetailScreen> {
  bool isLoading = true;
  Map<String, dynamic>? data;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    try {
      final response = await http.get(ApiConfig.buildUri('/predict/${widget.ticker}'));
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
        iconTheme: IconThemeData(color: Theme.of(context).textTheme.bodyLarge?.color),
        title: Text(widget.ticker, style: TextStyle(color: Theme.of(context).textTheme.bodyLarge?.color)),
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
    return SingleChildScrollView(
      padding: const EdgeInsets.all(25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeaderCard(),
          const SizedBox(height: 25),
          Text("AI Analysis", style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 15),
          _buildAIRecommendationCard(),
          const SizedBox(height: 40),
          _buildDecisionButtons(),
        ],
      ),
    );
  }

  Widget _buildHeaderCard() {
    final String price = (data!['precio'] ?? data!['price'] ?? '0.00').toString();
    
    final List ohlcRaw = data!['ohlc'] is List ? data!['ohlc'] : [];
    final List<Candle> candles = ohlcRaw.map((e) {
      return Candle(
        date: DateTime.parse(e['date']),
        high: (e['high'] as num).toDouble(),
        low: (e['low'] as num).toDouble(),
        open: (e['open'] as num).toDouble(),
        close: (e['close'] as num).toDouble(),
        volume: (e['volume'] as num).toDouble()
      );
    }).toList().reversed.toList(); // Candlesticks lib necesita el más reciente primero

    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(color: Theme.of(context).cardColor, borderRadius: BorderRadius.circular(25)),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(widget.ticker, style: GoogleFonts.poppins(fontSize: 35, fontWeight: FontWeight.bold, color: Colors.white)),
              Text("\$${double.parse(price).toStringAsFixed(2)}", style: GoogleFonts.poppins(fontSize: 28, color: Colors.lightBlueAccent, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            height: 350,
            child: candles.isNotEmpty
              ? Theme(
                  data: ThemeData.dark(),
                  child: Candlesticks(
                    candles: candles,
                  ),
                )
              : const Center(child: Icon(Icons.show_chart, size: 50, color: Colors.grey)),
          ),
        ],
      ),
    );
  }

  Widget _buildAIRecommendationCard() {
  // Obtenemos la recomendación y la pasamos a minúsculas para comparar
  final String rawRec = (data!['recomendacion'] ?? 'esperar').toString().toLowerCase();
  
  // Tu lógica de Python devuelve "comprar" o "no_comprar"
  bool isBuy = rawRec.contains("comprar");

  return Container(
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: isBuy ? const Color(0xFF1B5E20).withOpacity(0.2) : const Color(0xFFBF360C).withOpacity(0.2),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: isBuy ? Colors.greenAccent.withOpacity(0.3) : Colors.redAccent.withOpacity(0.3))
    ),
    child: Row(
      children: [
        Icon(Icons.auto_awesome, color: isBuy ? Colors.greenAccent : Colors.redAccent),
        const SizedBox(width: 15),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "ANÁLISIS DE IA",
                style: GoogleFonts.poppins(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.grey[400]),
              ),
              Text(
                rawRec.toUpperCase(), // Mostrará "COMPRAR" o "NO_COMPRAR"
                style: GoogleFonts.poppins(
                  fontWeight: FontWeight.bold, 
                  fontSize: 18,
                  color: isBuy ? Colors.greenAccent : Colors.redAccent
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
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text("No comprar")
          )
        ),
        const SizedBox(width: 15),
        Expanded(
          child: ElevatedButton(
            onPressed: _showBuyDialog, 
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.lightBlueAccent,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text("Comprar")
          )
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
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Decisión registrada: $decision'), backgroundColor: Colors.lightBlueAccent));
      }
    } catch (e) {
      debugPrint("Error saving decision: $e");
    }
  }

  void _showBuyDialog() {
    final TextEditingController qtyController = TextEditingController(text: "1");
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Comprar ${widget.ticker}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text("Precio actual: \$${(data!['precio'] ?? 0.0).toStringAsFixed(2)}"),
            const SizedBox(height: 15),
            TextField(
              controller: qtyController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: "Cantidad de acciones"),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
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
        ApiConfig.buildUri('/trade/buy?ticker=${widget.ticker}&quantity=$quantity'),
        headers: {'Authorization': 'Bearer $token'},
      );

      final resData = json.decode(response.body);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(resData['message']),
            backgroundColor: resData['status'] == 'success' ? Colors.green : Colors.red,
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