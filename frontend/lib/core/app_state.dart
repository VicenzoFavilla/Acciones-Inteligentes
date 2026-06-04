import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../config/api_config.dart';

class AppState extends ChangeNotifier {
  bool _isProMode = false;
  bool get isProMode => _isProMode;

  List<dynamic> _watchlist = [];
  List<dynamic> get watchlist => _watchlist;
  bool _isLoadingWatchlist = false;
  bool get isLoadingWatchlist => _isLoadingWatchlist;

  void toggleProMode() {
    _isProMode = !_isProMode;
    notifyListeners();
    _saveSettings();
  }

  Future<void> fetchWatchlist() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    if (token == null) return;

    _isLoadingWatchlist = true;
    notifyListeners();

    try {
      final response = await http.get(
        ApiConfig.buildUri('/user/watchlist'),
        headers: {'Authorization': 'Bearer $token'},
      );
      if (response.statusCode == 200) {
        _watchlist = json.decode(response.body)['watchlist'] ?? [];
      }
    } catch (e) {
      debugPrint("Error fetching watchlist: $e");
    } finally {
      _isLoadingWatchlist = false;
      notifyListeners();
    }
  }

  Future<bool> toggleWatchlist(String ticker) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    if (token == null) return false;

    ticker = ticker.toUpperCase();
    final isFav = _watchlist.any((stock) => stock['ticker'] == ticker);

    // Optimistic update
    if (isFav) {
      _watchlist.removeWhere((stock) => stock['ticker'] == ticker);
    } else {
      _watchlist.add({'ticker': ticker, 'nombre': ticker});
    }
    notifyListeners();

    try {
      final response = isFav
          ? await http.delete(
              ApiConfig.buildUri('/user/watchlist/$ticker'),
              headers: {'Authorization': 'Bearer $token'},
            )
          : await http.post(
              ApiConfig.buildUri('/user/watchlist/$ticker'),
              headers: {'Authorization': 'Bearer $token'},
            );

      if (response.statusCode != 200) {
        await fetchWatchlist(); // Revert on server error
        return false;
      }
      return true;
    } catch (e) {
      await fetchWatchlist(); // Revert on network error
      return false;
    }
  }

  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _isProMode = prefs.getBool('is_pro_mode') ?? false;
    notifyListeners();
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_pro_mode', _isProMode);
  }
}
