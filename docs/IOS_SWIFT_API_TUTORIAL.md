# iOS Swift API Tutorial

## Who This Tutorial Is For

This tutorial is for students and beginner iPhone developers who want to use the meteorological APIs in a small Swift application.

We will build a simple educational app that:

1. connects to the API
2. checks the API version
3. searches for a place
4. downloads forecast data
5. shows the result on screen

Related documents:

- Endpoint reference: [API_ENDPOINTS.md](API_ENDPOINTS.md)
- Python beginner tutorial: [PYTHON_API_TUTORIAL.md](PYTHON_API_TUTORIAL.md)
- Android equivalent tutorial: [ANDROID_KOTLIN_API_TUTORIAL.md](ANDROID_KOTLIN_API_TUTORIAL.md)

## 1. What We Are Building

We will create a simple iOS app with:

- a text field for the place name
- one button to search
- one button to request a forecast
- one text area to display the result

The goal is to understand how API calls work in Swift, not to build a complete commercial app.

## 2. What You Need

You need:

- Xcode
- a recent iOS simulator or device
- basic Swift knowledge
- internet access to the API

This tutorial uses:

- Swift
- `URLSession`
- `Codable`
- `async/await`

## 3. Create the Project

In Xcode:

1. create a new iOS App project
2. name it `SimpleWeatherApp`
3. choose Swift
4. choose SwiftUI for the interface

## 4. Understand the Base URL

We will use:

```text
https://api.meteo.uniparthenope.it
```

In Swift, we build full URLs by adding paths such as `/version` or `/places/search/byname/autocomplete?term=nap`.

## 5. Create the Data Models

Create a file called `ApiModels.swift`:

```swift
import Foundation

struct VersionResponse: Codable {
    let version: String
    let environment: String
}

struct PlaceSuggestion: Codable, Identifiable {
    let id: String
    let label: String
}
```

## 6. Create the API Client

Create a file called `WeatherApiClient.swift`:

```swift
import Foundation

final class WeatherApiClient {
    private let baseURL = "https://api.meteo.uniparthenope.it"

    func getVersion() async throws -> VersionResponse {
        let url = URL(string: "\(baseURL)/version")!
        let (data, _) = try await URLSession.shared.data(from: url)
        return try JSONDecoder().decode(VersionResponse.self, from: data)
    }

    func autocompletePlaces(term: String) async throws -> [PlaceSuggestion] {
        var components = URLComponents(string: "\(baseURL)/places/search/byname/autocomplete")!
        components.queryItems = [
            URLQueryItem(name: "term", value: term)
        ]

        let (data, _) = try await URLSession.shared.data(from: components.url!)
        return try JSONDecoder().decode([PlaceSuggestion].self, from: data)
    }

    func getForecast(product: String, place: String) async throws -> [String: Any] {
        let url = URL(string: "\(baseURL)/products/\(product)/forecast/\(place)")!
        let (data, _) = try await URLSession.shared.data(from: url)
        let object = try JSONSerialization.jsonObject(with: data, options: [])
        return object as? [String: Any] ?? [:]
    }
}
```

Why do we use `[String: Any]` for the forecast?

- it keeps the first version of the app simple
- forecast payloads may change shape depending on product and parameters
- once you inspect the JSON, you can replace it with specific `Codable` models

## 7. Create the View Model

Create `WeatherViewModel.swift`:

```swift
import Foundation

@MainActor
final class WeatherViewModel: ObservableObject {
    @Published var placeText = ""
    @Published var outputText = "Results will appear here"
    @Published var selectedPlaceId: String?

    private let api = WeatherApiClient()

    func loadVersion() async {
        do {
            let version = try await api.getVersion()
            outputText = "Connected to API version \(version.version) in \(version.environment)"
        } catch {
            outputText = "Connection error: \(error.localizedDescription)"
        }
    }

    func searchPlace() async {
        let trimmed = placeText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            outputText = "Please type a place name."
            return
        }

        do {
            let results = try await api.autocompletePlaces(term: trimmed)
            if let first = results.first {
                selectedPlaceId = first.id
                outputText = "Selected place: \(first.label)\nPlace id: \(first.id)"
            } else {
                outputText = "No places found."
            }
        } catch {
            outputText = "Search error: \(error.localizedDescription)"
        }
    }

    func loadForecast() async {
        guard let placeId = selectedPlaceId else {
            outputText = "Search for a place first."
            return
        }

        do {
            let forecast = try await api.getForecast(product: "wrf5", place: placeId)
            let keys = forecast.keys.sorted().joined(separator: ", ")
            outputText = "Forecast loaded for \(placeId)\nTop-level keys: \(keys)"
        } catch {
            outputText = "Forecast error: \(error.localizedDescription)"
        }
    }
}
```

## 8. Create the SwiftUI Interface

Replace the main content view with:

```swift
import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = WeatherViewModel()

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Simple Weather App")
                .font(.title)

            TextField("Type a place, for example Napoli", text: $viewModel.placeText)
                .textFieldStyle(.roundedBorder)

            Button("Search Place") {
                Task {
                    await viewModel.searchPlace()
                }
            }

            Button("Load Forecast") {
                Task {
                    await viewModel.loadForecast()
                }
            }

            ScrollView {
                Text(viewModel.outputText)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            Spacer()
        }
        .padding()
        .task {
            await viewModel.loadVersion()
        }
    }
}
```

## 9. Why This Example Is Useful

This small app teaches:

- how to call HTTP endpoints with `URLSession`
- how to decode JSON with `Codable`
- how to pass query parameters with `URLComponents`
- how to update the interface safely with `@MainActor`
- how to perform asynchronous API calls with `async/await`

## 10. Good Practices

- Start with `/version` because it is simple and easy to test.
- Use `URLComponents` when query parameters are involved.
- Show user-friendly error messages.
- Keep networking code separate from interface code.
- Inspect large forecast JSON responses before creating detailed models.

## 11. Possible Extensions

After this tutorial, try:

- showing multiple place suggestions in a SwiftUI `List`
- creating a dedicated forecast model for one product
- downloading and displaying weather images
- adding a favorite places screen
- refreshing data automatically

For a route-by-route reference and more examples, continue with [API_ENDPOINTS.md](API_ENDPOINTS.md).
