This is a currently work-in-progress car market analysis app. 

Its intended functionality is scraping car sales data from two sites, one locally Romanian (Autovit.ro), and a way larger German/European marketplace (Mobile.de), and training prediction models on data from both, comparing both results from different models on the same marketplace, and the predicted values on both marketplaces for similar models.  

Currently functional features:  

Robust scraper and data cleaning pipeline for Autovit.ro  
Several trained machine learning algorithms (on older data, for now), for the site.  
Robust extraction of all possible brands from the site for a cleaner classification of data.  

Planned features:  

Mimic the scraping and cleaning logic for Mobile.de, then apply similar machine learning pipelines  
Implement a proper backend through FastAPI and have a frontend interactive dashboard for data visualisation.  
Package models for user exploration without access to the actual .csv scraped data (to be implemented before the dashboard).  