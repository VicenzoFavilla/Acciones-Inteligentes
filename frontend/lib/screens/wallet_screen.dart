import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class WalletScreen extends StatefulWidget {
  const WalletScreen({super.key});

  @override
  _WalletScreenState createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> {
  double balance = 0.0;
  double totalEquity = 0.0;
  List<dynamic> portfolioDetails = [];
  bool isLoading = true;
  String? token;

  @override
  void initState() {
    super.initState();
    _fetchWalletData();
  }

  Future<void> _fetchWalletData() async {
    final prefs = await SharedPreferences.getInstance();
    token = prefs.getString('auth_token');
    
    if (token == null) {
      if (mounted) setState(() => isLoading = false);
      return;
    }

    try {
      final response = await http.get(
        Uri.parse('http://127.0.0.1:8001/wallet/info'),
        headers: {'Authorization': 'Bearer $token'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          balance = (data['wallet']['balance'] as num).toDouble();
          totalEquity = (data['wallet']['total_equity'] as num).toDouble();
          portfolioDetails = List<dynamic>.from(data['wallet']['portfolio_details'] ?? []);
        });
      } else {
        debugPrint("Server error wallet: ${response.statusCode}");
      }
      if (mounted) setState(() => isLoading = false);
    } catch (e) {
      debugPrint("Error fetching wallet: $e");
      if (mounted) setState(() => isLoading = false);
    }
  }

  Future<void> _depositFunds(double amount) async {
    try {
      final response = await http.post(
        Uri.parse('http://127.0.0.1:8001/wallet/deposit?amount=$amount'),
        headers: {'Authorization': 'Bearer $token'},
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200) {
        if (data['status'] == 'success') {
          _fetchWalletData();
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(data['message'] ?? 'Depósito exitoso'), backgroundColor: Colors.green),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(data['message'] ?? 'Error al depositar'), backgroundColor: Colors.red),
          );
        }
      }
    } catch (e) {
      debugPrint("Error depositing: $e");
    }
  }

  void _showDepositDialog() {
    final TextEditingController amountController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Depositar Fondos'),
        content: TextField(
          controller: amountController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(hintText: "Monto a depositar"),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          ElevatedButton(
            onPressed: () {
              final double? amount = double.tryParse(amountController.text);
              if (amount != null && amount > 0) {
                _depositFunds(amount);
                Navigator.pop(context);
              }
            },
            child: const Text('Depositar'),
          ),
        ],
      ),
    );
  }

  Future<void> _sellStock(String ticker, int quantity) async {
    try {
      final response = await http.post(
        Uri.parse('http://127.0.0.1:8001/trade/sell?ticker=$ticker&quantity=$quantity'),
        headers: {'Authorization': 'Bearer $token'},
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200) {
        if (data['status'] == 'success') {
          _fetchWalletData();
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(data['message'] ?? 'Venta exitosa'), backgroundColor: Colors.green),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(data['message'] ?? 'Error al vender'), backgroundColor: Colors.red),
          );
        }
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(data['message'] ?? 'Error del servidor'), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      debugPrint("Error selling: $e");
    }
  }

  void _showSellDialog(String ticker, int maxQuantity) {
    final TextEditingController quantityController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Vender $ticker'),
        content: TextField(
          controller: quantityController,
          keyboardType: TextInputType.number,
          decoration: InputDecoration(hintText: "Cantidad (Máx: $maxQuantity)"),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent, foregroundColor: Colors.white),
            onPressed: () {
              final int? quantity = int.tryParse(quantityController.text);
              if (quantity != null && quantity > 0 && quantity <= maxQuantity) {
                _sellStock(ticker, quantity);
                Navigator.pop(context);
              }
            },
            child: const Text('Vender'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text("Mi Billetera", style: GoogleFonts.poppins(fontWeight: FontWeight.bold)),
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(25),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildBalanceCard(),
                  const SizedBox(height: 30),
                  Text("Mi Portafolio", style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.lightBlueAccent)),
                  const SizedBox(height: 15),
                  _buildPortfolioList(),
                ],
              ),
            ),
    );
  }

  Widget _buildBalanceCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0D47A1), Color(0xFF00BFFF)],
        ),
        borderRadius: BorderRadius.circular(25),
        boxShadow: [BoxShadow(color: Colors.lightBlueAccent.withAlpha(51), blurRadius: 15, offset: const Offset(0, 10))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Patrimonio Total", style: GoogleFonts.poppins(color: Colors.white70, fontSize: 14)),
          Text("\$${totalEquity.toStringAsFixed(2)}", 
            style: GoogleFonts.poppins(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
          const SizedBox(height: 15),
          Divider(color: Colors.white.withAlpha(51)),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Saldo en Efectivo", style: GoogleFonts.poppins(color: Colors.white70, fontSize: 12)),
                  Text("\$${balance.toStringAsFixed(2)}", style: GoogleFonts.poppins(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                ],
              ),
              ElevatedButton(
                onPressed: _showDepositDialog,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.white.withAlpha(51),
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text("Depositar"),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPortfolioList() {
    if (portfolioDetails.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(20),
        child: const Center(
          child: Text(
            "No tienes acciones en posesión.", 
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey),
          ),
        ),
      );
    }

    return Column(
      children: portfolioDetails.map<Widget>((asset) {
        final String ticker = asset['ticker'];
        final int quantity = asset['quantity'];
        final double avgPrice = (asset['average_price'] as num).toDouble();
        final double pnlPct = (asset['pnl_pct'] as num).toDouble();
        final double pnlAbs = (asset['pnl_abs'] as num).toDouble();
        
        final bool isUp = pnlAbs >= 0;
        final Color pnlColor = isUp ? Colors.greenAccent : Colors.redAccent;

        return Container(
          margin: const EdgeInsets.only(bottom: 15),
          padding: const EdgeInsets.all(15),
          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Theme.of(context).dividerColor.withAlpha(26)),
            boxShadow: [BoxShadow(color: Colors.black.withAlpha(13), blurRadius: 10)],
          ),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        backgroundColor: Colors.lightBlueAccent.withAlpha(26),
                        child: Text(ticker[0], style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.lightBlueAccent)),
                      ),
                      const SizedBox(width: 15),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(ticker, style: GoogleFonts.poppins(fontWeight: FontWeight.bold, fontSize: 16, color: Theme.of(context).textTheme.bodyLarge?.color)),
                          Text("$quantity acciones", style: GoogleFonts.poppins(color: Colors.grey, fontSize: 13)),
                        ],
                      ),
                    ],
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        "${isUp ? '+' : ''}${pnlPct.toStringAsFixed(2)}%", 
                        style: GoogleFonts.poppins(fontWeight: FontWeight.bold, fontSize: 15, color: pnlColor)
                      ),
                      Text(
                        "${isUp ? '+' : ''}\$${pnlAbs.toStringAsFixed(2)}", 
                        style: GoogleFonts.poppins(fontSize: 12, color: pnlColor.withAlpha(204))
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 15),
              Divider(color: Theme.of(context).dividerColor.withAlpha(26), height: 1),
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    "P. Promedio: \$${avgPrice.toStringAsFixed(2)}", 
                    style: GoogleFonts.poppins(color: Colors.grey[500], fontSize: 12)
                  ),
                  GestureDetector(
                    onTap: () => _showSellDialog(ticker, quantity),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.redAccent.withAlpha(26),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Text("Vender", style: TextStyle(color: Colors.redAccent, fontSize: 12, fontWeight: FontWeight.bold)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
