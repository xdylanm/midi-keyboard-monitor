package com.example.midi_keyboard_monitor_app

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.content.Intent
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity() {
	companion object {
		private const val REQUEST_PERMISSIONS = 1001
		private const val REQUEST_ENABLE_BT = 1002
	}

	override fun onCreate(savedInstanceState: Bundle?) {
		super.onCreate(savedInstanceState)
		checkAndRequestPermissions()
	}

	override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
		super.configureFlutterEngine(flutterEngine)
		MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "midi_keyboard_monitor_app/bluetooth").setMethodCallHandler { call, result ->
			if (call.method == "requestEnable") {
				val bluetoothAdapter: BluetoothAdapter? = BluetoothAdapter.getDefaultAdapter()
				if (bluetoothAdapter == null) {
					result.error("NO_BT", "Device has no Bluetooth adapter", null)
					return@setMethodCallHandler
				}
				if (bluetoothAdapter.isEnabled) {
					result.success(true)
					return@setMethodCallHandler
				}
				val enableBtIntent = Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)
				startActivityForResult(enableBtIntent, REQUEST_ENABLE_BT)
				result.success(true)
			} else {
				result.notImplemented()
			}
		}
	}

	private fun checkAndRequestPermissions() {
		val perms = ArrayList<String>()

		// For Android 12+ include the new Bluetooth runtime permissions
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
			perms.add(Manifest.permission.BLUETOOTH_SCAN)
			perms.add(Manifest.permission.BLUETOOTH_CONNECT)
		}

		// Location permission is still required on many devices for BLE scanning
		perms.add(Manifest.permission.ACCESS_FINE_LOCATION)

		val toRequest = perms.filter {
			ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
		}

		if (toRequest.isNotEmpty()) {
			ActivityCompat.requestPermissions(this, toRequest.toTypedArray(), REQUEST_PERMISSIONS)
		}
	}
}
