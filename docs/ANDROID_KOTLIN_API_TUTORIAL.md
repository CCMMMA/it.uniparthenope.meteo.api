# Android Kotlin API Tutorial

## Who This Tutorial Is For

This tutorial is written for students and beginner Android developers who want to build a simple weather application using Kotlin and the `it.uniparthenope.meteo.api` service.

The tutorial is intentionally step by step. We will:

1. create a simple Android project
2. connect the app to the API
3. download JSON data
4. search for a place
5. request a forecast
6. show the results on screen

Related documents:

- Endpoint reference: [API_ENDPOINTS.md](API_ENDPOINTS.md)
- Python beginner tutorial: [PYTHON_API_TUTORIAL.md](PYTHON_API_TUTORIAL.md)
- iOS equivalent tutorial: [IOS_SWIFT_API_TUTORIAL.md](IOS_SWIFT_API_TUTORIAL.md)

The governed API is available under `/api/v1`. New Android integrations should
use `GET /api/v1/products` and the related versioned product metadata routes.
Existing tutorial calls remain supported on legacy paths while other resource
families are migrated.

## 1. What We Are Building

We will build a very small Android app with:

- one text field where the user writes a place name
- one button to search the API
- one button to load a forecast for a selected place
- one text area to show the result

This is not meant to be a full production app. It is a learning project that shows the main ideas clearly.

## 2. What You Need

You need:

- Android Studio
- a recent Android SDK
- basic Kotlin knowledge
- internet access to the API server

In this tutorial we use:

- Kotlin
- Retrofit for HTTP requests
- Gson for JSON parsing
- Coroutines for background work

## 3. Create the Project

In Android Studio:

1. create a new project
2. choose `Empty Views Activity`
3. name it `SimpleWeatherApp`
4. choose Kotlin as the language

## 4. Add the Dependencies

Open `app/build.gradle` and add these dependencies:

```gradle
implementation "com.squareup.retrofit2:retrofit:2.11.0"
implementation "com.squareup.retrofit2:converter-gson:2.11.0"
implementation "org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1"
```

Also make sure internet access is enabled in `AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

## 5. Understand the Base URL

We will use this base URL in the examples:

```text
https://api.meteo.uniparthenope.it/
```

Notice the final `/`. Retrofit expects the base URL to end with a slash.

## 6. Create the Data Classes

Create a file called `ApiModels.kt`:

```kotlin
data class VersionResponse(
    val version: String,
    val environment: String
)

data class PlaceSuggestion(
    val id: String,
    val label: String
)
```

These classes describe the JSON we expect from the API.

## 7. Create the Retrofit Interface

Create a file called `WeatherApiService.kt`:

```kotlin
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface WeatherApiService {
    @GET("version")
    suspend fun getVersion(): VersionResponse

    @GET("places/search/byname/autocomplete")
    suspend fun autocompletePlaces(
        @Query("term") term: String
    ): List<PlaceSuggestion>

    @GET("products/{product}/forecast/{place}")
    suspend fun getForecast(
        @Path("product") product: String,
        @Path("place") place: String
    ): Map<String, Any>
}
```

Why do we use `Map<String, Any>` for the forecast?

- because forecast payloads can be large and nested
- for a beginner project it is fine to inspect the structure first
- later you can replace it with specific Kotlin data classes

## 8. Create the Retrofit Client

Create a file called `ApiClient.kt`:

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private const val BASE_URL = "https://api.meteo.uniparthenope.it/"

    val service: WeatherApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(WeatherApiService::class.java)
    }
}
```

## 9. Create a Simple Layout

Replace the activity layout with something minimal like this:

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp">

    <EditText
        android:id="@+id/placeInput"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:hint="Type a place, for example Napoli" />

    <Button
        android:id="@+id/searchButton"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Search Place" />

    <Button
        android:id="@+id/forecastButton"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Load Forecast" />

    <TextView
        android:id="@+id/outputView"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:paddingTop="16dp"
        android:text="Results will appear here" />

</LinearLayout>
```

## 10. Write the Activity Code

In `MainActivity.kt`:

```kotlin
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var placeInput: EditText
    private lateinit var searchButton: Button
    private lateinit var forecastButton: Button
    private lateinit var outputView: TextView

    private var selectedPlaceId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        placeInput = findViewById(R.id.placeInput)
        searchButton = findViewById(R.id.searchButton)
        forecastButton = findViewById(R.id.forecastButton)
        outputView = findViewById(R.id.outputView)

        searchButton.setOnClickListener {
            searchPlace()
        }

        forecastButton.setOnClickListener {
            loadForecast()
        }
    }

    private fun searchPlace() {
        val term = placeInput.text.toString().trim()
        if (term.isEmpty()) {
            outputView.text = "Please type a place name."
            return
        }

        lifecycleScope.launch {
            try {
                val results = ApiClient.service.autocompletePlaces(term)
                if (results.isEmpty()) {
                    outputView.text = "No places found."
                } else {
                    val first = results.first()
                    selectedPlaceId = first.id
                    outputView.text = "Selected place: ${first.label}\nPlace id: ${first.id}"
                }
            } catch (e: Exception) {
                outputView.text = "Search error: ${e.message}"
            }
        }
    }

    private fun loadForecast() {
        val placeId = selectedPlaceId
        if (placeId == null) {
            outputView.text = "Search for a place first."
            return
        }

        lifecycleScope.launch {
            try {
                val forecast = ApiClient.service.getForecast("wrf5", placeId)
                val keys = forecast.keys.joinToString(", ")
                outputView.text = "Forecast loaded for $placeId\nTop-level keys: $keys"
            } catch (e: Exception) {
                outputView.text = "Forecast error: ${e.message}"
            }
        }
    }
}
```

## 11. What This App Teaches

This app already teaches several important concepts:

- how to call a REST API from Android
- how to send query parameters
- how to use path parameters
- how to work safely in the background with coroutines
- how to show results in the interface

## 12. A Real Improvement: Add Version Check

A useful beginner exercise is adding a version check when the app starts:

```kotlin
lifecycleScope.launch {
    try {
        val version = ApiClient.service.getVersion()
        outputView.text = "Connected to API version ${version.version} (${version.environment})"
    } catch (e: Exception) {
        outputView.text = "Cannot contact API: ${e.message}"
    }
}
```

This helps you test connectivity before trying more complex endpoints.

## 13. Good Practices

- Do not run network requests on the main thread.
- Always show a helpful message when a request fails.
- Start with small endpoints such as `/version` and `/places/search/byname/autocomplete`.
- Inspect the JSON before creating large data classes.
- Keep the base URL in one place.

## 14. Next Steps

After this tutorial, you can improve the app by:

- showing the list of all matching places in a `RecyclerView`
- parsing forecast JSON into stronger data classes
- downloading product images
- saving favorite places
- adding a loading spinner

For the exact endpoint behavior and more examples, continue with [API_ENDPOINTS.md](API_ENDPOINTS.md).
