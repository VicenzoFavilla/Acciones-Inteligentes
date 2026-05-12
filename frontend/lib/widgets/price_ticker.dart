import 'package:flutter/material.dart';

class PriceTicker extends StatefulWidget {
  final double price;
  final double? fontSize;
  final FontWeight? fontWeight;
  final Color? color;

  const PriceTicker({
    super.key,
    required this.price,
    this.fontSize,
    this.fontWeight,
    this.color,
  });

  @override
  State<PriceTicker> createState() => _PriceTickerState();
}

class _PriceTickerState extends State<PriceTicker> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Color?> _animation;
  double _lastPrice = 0.0;

  @override
  void initState() {
    super.initState();
    _lastPrice = widget.price;
    _controller = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    _animation = ColorTween(
      begin: Colors.white,
      end: Colors.white,
    ).animate(_controller);
  }

  @override
  void didUpdateWidget(PriceTicker oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.price != _lastPrice) {
      final bool isUp = widget.price > _lastPrice;
      _lastPrice = widget.price;
      
      _animation = ColorTween(
        begin: isUp ? Colors.greenAccent : Colors.redAccent,
        end: widget.color ?? (Theme.of(context).brightness == Brightness.dark ? Colors.white : Colors.black),
      ).animate(_controller);
      
      _controller.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Text(
          "\$${widget.price.toStringAsFixed(2)}",
          style: TextStyle(
            fontSize: widget.fontSize ?? 16,
            fontWeight: widget.fontWeight ?? FontWeight.bold,
            color: _animation.value,
          ),
        );
      },
    );
  }
}
