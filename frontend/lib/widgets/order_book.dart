import 'package:flutter/material.dart';
import 'dart:math';

class OrderBook extends StatelessWidget {
  final double basePrice;
  const OrderBook({super.key, required this.basePrice});

  @override
  Widget build(BuildContext context) {
    // Simular datos de libro de órdenes basados en el precio base
    final List<Map<String, dynamic>> bids = List.generate(10, (i) {
      final price = basePrice - (i * 0.05) - (Random().nextDouble() * 0.02);
      final size = (Random().nextDouble() * 500).toStringAsFixed(2);
      return {"price": price, "size": size};
    });

    final List<Map<String, dynamic>> asks = List.generate(10, (i) {
      final price = basePrice + (i * 0.05) + (Random().nextDouble() * 0.02);
      final size = (Random().nextDouble() * 500).toStringAsFixed(2);
      return {"price": price, "size": size};
    }).reversed.toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 8.0),
          child: Text("Libro de Órdenes (Pro)", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70)),
        ),
        Row(
          children: [
            Expanded(child: Text("Precio", style: TextStyle(color: Colors.grey[600], fontSize: 10))),
            Expanded(child: Text("Cantidad", style: TextStyle(color: Colors.grey[600], fontSize: 10), textAlign: TextAlign.right)),
          ],
        ),
        const Divider(height: 10, color: Colors.white10),
        // ASKS (Rojo)
        ...asks.map((a) => _buildRow(a["price"], a["size"], Colors.redAccent.withAlpha(51))),
        
        // PRECIO ACTUAL
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 10.0),
          child: Center(
            child: Text(
              "\$${basePrice.toStringAsFixed(2)}",
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.lightBlueAccent),
            ),
          ),
        ),
        
        // BIDS (Verde)
        ...bids.map((b) => _buildRow(b["price"], b["size"], Colors.greenAccent.withAlpha(51))),
      ],
    );
  }

  Widget _buildRow(double price, String size, Color bgColor) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 2.0),
      color: bgColor,
      child: Row(
        children: [
          Expanded(child: Text(price.toStringAsFixed(2), style: const TextStyle(fontSize: 11, color: Colors.white))),
          Expanded(child: Text(size, style: const TextStyle(fontSize: 11, color: Colors.white70), textAlign: TextAlign.right)),
        ],
      ),
    );
  }
}
