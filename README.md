GB & IRE Horse Racing Analytics

Problem Statement:
Working at Ladbrokes, I encountered many customers and colleagues facing a common challenge: the only way to check statistics and analytics for horse racing was through the daily newspaper. For novices, this method can be extremely difficult to read and interpret, especially when it comes to understanding horse form, odds, and placing bets. Calculating potential outcomes manually adds another layer of complexity.

Project Goals:
The purpose of this application is not to serve as a betting platform, but rather to create a horse racing analytics wiki that is:
- Accessible: Easy to navigate and understand, even for beginners.
- Informative: Provides detailed race and runner information, including jockey, trainer, odds, and favourite detection.
- Interactive: Allows users to explore upcoming and finished races with clear visual indicators for favourites, winners, and non-runners.
- Seamless: Reduces the need for manual calculations and newspaper analysis by aggregating and presenting data from reliable sources like Betfair and Timeform.

By centralizing data in a user-friendly format, the app aims to streamline the process of understanding horse racing markets, making it more approachable for users of all experience levels.

Choice of Data:
The app uses Betfair's delayed API to access UK and Ireland horse racing markets, including race times, runners, jockeys, trainers, odds, and non-runner status. Live data costs £299, so the delayed feed provides a cost-effective alternative for analytics and simulations.

Timeform data was considered for horse form and expert comments, but programmatic access requires permission. Instead, the app links to Timeform pages for detailed horse information. This combination ensures the app provides useful insights while remaining accessible and legal.

Extract, Transform, Load:
- Extract: Data is pulled from the Betfair API, including market details, runners, jockeys, trainers, odds, and non-runner status.
- Transform: Data is processed to calculate favorites, identify winners in finished races, and organize runner metadata for display. Dates and times are converted to local time for readability.
- Load: Processed data is displayed in Streamlit pages for upcoming and finished races, with expandable sections for each horse and links to Timeform for additional info.

Technical Depth (Including Testing):
All API interactions and data processing logic were first developed and tested in bet_fair_test.ipynb before being integrated into the Streamlit application. Key testing areas included:

- API Authentication: Verified certificate-based login functionality
- Market Filtering: Tested date range filters and market type filters for accurate data retrieval
- Data Extraction: Validated extraction of runner metadata including cloth numbers, jockeys, and trainers
- Odds Retrieval: Tested fetching best back odds from market books for favorite detection
- Non-Runner Detection: Verified reliable detection of removed runners through market book status checks
- Winner Identification: Tested multiple methods for identifying winners in finished races
- Data Formatting: Validated display formatting for races and horses before UI implementation

This iterative development approach ensured robust error handling, proper timezone conversions, and efficient data processing before deployment to the Streamlit interface.

The application includes a comprehensive test suite using pytest to validate key data processing, transformation, and cleaning functions. The test suite focuses on seven essential test cases that cover critical business logic:

- Data Extraction and Cleaning: Tests the get_runner_info() function to ensure missing metadata is handled gracefully with default "N/A" values, preventing application errors when data is incomplete.
- Odds Transformation: Validates the transformation of market book runner data into an odds map, ensuring accurate odds extraction from the Betfair API response structure.
- Favorite Identification: Tests the logic for identifying the favorite horse (lowest back odds) while correctly excluding non-runners, which is critical for accurate market insights.
- Non-Runner Detection: Verifies reliable detection of non-runners through status attribute checks, ensuring removed horses are properly identified and excluded from calculations.
- Winner Identification: Tests winner identification via position attributes, validating the core logic for displaying race results in finished races.
- Market Classification: Validates the splitting of markets into upcoming and finished categories based on current time, and ensures proper chronological sorting for display.
- Bet Calculations: Tests win bet calculations including profit, total return, ROI, and implied probability, ensuring the bet simulator provides accurate financial projections.

The test suite uses unittest.mock to create mock objects, allowing tests to run independently without requiring live API connections or Streamlit dependencies. This approach ensures fast, reliable testing of data processing logic while maintaining test isolation and repeatability.

Streamlit:
The app is built with Streamlit, providing an interactive web interface for exploring horse racing data. Streamlit was chosen for its simplicity, quick development cycle, and ability to create dynamic dashboards without extensive frontend development.

Key features implemented with Streamlit include:
- Sidebar Navigation: Quickly switch between Home, Upcoming Races, Finished Races, and Bet Simulator pages.
- Date Filters: Select today, tomorrow, or a custom date to view races.
- Expandable Race Cards: Each race shows runners, jockeys, and trainers, with indicators for favorites, non-runners, and winners.
- Market Insights: Highlights the most favored horse based on Betfair odds.
- Hyperlinks: Connects users to Timeform for further information.

Insights:
The app provides valuable insights including automatic favorite identification based on lowest back odds, clear non-runner detection, winner highlighting in finished races, and real-time bet calculations for profit, ROI, and implied probability. These features help users save time, centralize information, and understand horse racing markets more effectively.

Challenges and Takeaways:
Key challenges included initially retrieving data from the Betfair API, as connection and authentication were difficult to set up. Another limitation was that Betfair does not provide all the data needed for comprehensive analytics, as their insights rely on Timeform data. Attempts to extract data directly from Timeform were unsuccessful due to permission restrictions.

The main takeaway is that understanding these API limitations early helped shape the app’s design, focusing on what is feasible with available data while leaving room for future improvements. Iterative development in Jupyter notebooks before full Streamlit integration also helped ensure robust functionality.

Future Development:
If access to the Timeform API is granted, the app could include more detailed analytics for each horse, such as previous race times, win records, and performance on specific tracks. Users could also compare multiple horses for more informed decision-making. Other potential enhancements include data persistence for historical analysis, advanced jockey and trainer statistics,

Flow:
The application flow begins with user navigation to select a date and page. For upcoming races, markets are fetched and displayed with expandable sections for races and horses. For finished races, markets are fetched and winners are identified. The bet simulator allows users to select races and horses, enter bet details, and view calculated results. All data flows from the Betfair API through cached fetch functions, transformation helpers, and finally to Streamlit UI components.

