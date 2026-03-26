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
  Map<String, dynamic> portfolio = {};
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
          portfolio = Map<String, dynamic>.from(data['wallet']['portfolio'] ?? {});
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

      if (response.statusCode == 200) {
        _fetchWalletData();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Depósito de \$$amount exitoso')),
        );
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

      if (response.statusCode == 200) {
        _fetchWalletData();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Venta de $quantity acciones de $ticker exitosa')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Error al vender acciones')),
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
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        title: Text("Mi Billetera", style: GoogleFonts.poppins(color: Colors.black, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.black),
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
                  Text("Mi Portafolio", style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold)),
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
      padding: const EdgeInsets.all(30),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF2196F3), Color(0xFF21CBF3)]),
        borderRadius: BorderRadius.circular(25),
        boxShadow: [BoxShadow(color: Colors.blue.withOpacity(0.3), blurRadius: 15, offset: const Offset(0, 10))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Saldo Disponible", style: GoogleFonts.poppins(color: Colors.white70, fontSize: 16)),
          Text("\$${balance.toStringAsFixed(2)}", 
            style: GoogleFonts.poppins(color: Colors.white, fontSize: 35, fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _showDepositDialog,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: Colors.blueAccent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
            ),
            child: const Text("Depositar Fondos"),
          ),
        ],
      ),
    );
  }

  Widget _buildPortfolioList() {
    if (portfolio.isEmpty) {
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
      children: portfolio.entries.map((entry) {
        final String ticker = entry.key;
        final int quantity = entry.value;
        return Container(
          margin: const EdgeInsets.only(bottom: 15),
          padding: const EdgeInsets.all(15),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10)],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    backgroundColor: Colors.blue.withOpacity(0.1),
                    child: Text(ticker[0], style: const TextStyle(fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(width: 15),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(ticker, style: GoogleFonts.poppins(fontWeight: FontWeight.bold, fontSize: 16)),
                      Text("$quantity acciones", style: GoogleFonts.poppins(color: Colors.grey, fontSize: 13)),
                    ],
                  ),
                ],
              ),
              ElevatedButton(
                onPressed: () => _showSellDialog(ticker, quantity),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.redAccent.withOpacity(0.1),
                  foregroundColor: Colors.redAccent,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                child: const Text("Vender"),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
