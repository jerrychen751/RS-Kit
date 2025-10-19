import pytest
from datetime import datetime
from pydantic import ValidationError
from rskit.models.query import Query, SpatialExtent, TemporalExtent


class TestSpatialExtent:
    """Test cases for SpatialExtent class."""

    def test_spatial_extent_happy_path(self):
        """Test SpatialExtent with valid coordinates."""
        # Arrange
        lon_min, lon_max = -180.0, 180.0
        lat_min, lat_max = -90.0, 90.0
        crs = "EPSG:4326"
        
        # Act
        spatial = SpatialExtent(
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max,
            crs=crs
        )
        
        # Assert
        assert spatial.lon_min == lon_min
        assert spatial.lon_max == lon_max
        assert spatial.lat_min == lat_min
        assert spatial.lat_max == lat_max
        assert spatial.crs == crs

    def test_spatial_extent_default_crs(self):
        """Test SpatialExtent with default CRS."""
        # Arrange
        lon_min, lon_max = 0.0, 10.0
        lat_min, lat_max = 0.0, 10.0
        
        # Act
        spatial = SpatialExtent(
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max
        )
        
        # Assert
        assert spatial.crs == "EPSG:4326"

    def test_spatial_extent_lon_min_boundary_values(self):
        """Test SpatialExtent with longitude minimum boundary values."""
        # Arrange
        lon_min = -180.0
        lon_max = 0.0
        lat_min, lat_max = 0.0, 10.0
        
        # Act
        spatial = SpatialExtent(
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max
        )
        
        # Assert
        assert spatial.lon_min == -180.0

    def test_spatial_extent_lon_max_boundary_values(self):
        """Test SpatialExtent with longitude maximum boundary values."""
        # Arrange
        lon_min = 0.0
        lon_max = 180.0
        lat_min, lat_max = 0.0, 10.0
        
        # Act
        spatial = SpatialExtent(
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max
        )
        
        # Assert
        assert spatial.lon_max == 180.0

    def test_spatial_extent_lat_min_boundary_values(self):
        """Test SpatialExtent with latitude minimum boundary values."""
        # Arrange
        lon_min, lon_max = 0.0, 10.0
        lat_min = -90.0
        lat_max = 0.0
        
        # Act
        spatial = SpatialExtent(
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max
        )
        
        # Assert
        assert spatial.lat_min == -90.0

    def test_spatial_extent_lat_max_boundary_values(self):
        """Test SpatialExtent with latitude maximum boundary values."""
        # Arrange
        lon_min, lon_max = 0.0, 10.0
        lat_min = 0.0
        lat_max = 90.0
        
        # Act
        spatial = SpatialExtent(
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max
        )
        
        # Assert
        assert spatial.lat_max == 90.0

    def test_spatial_extent_lon_min_below_minimum(self):
        """Test SpatialExtent with longitude minimum below -180."""
        # Arrange
        lon_min = -181.0
        lon_max = 0.0
        lat_min, lat_max = 0.0, 10.0
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SpatialExtent(
                lon_min=lon_min,
                lon_max=lon_max,
                lat_min=lat_min,
                lat_max=lat_max
            )
        
        assert "greater than or equal to -180" in str(exc_info.value)

    def test_spatial_extent_lon_max_above_maximum(self):
        """Test SpatialExtent with longitude maximum above 180."""
        # Arrange
        lon_min = 0.0
        lon_max = 181.0
        lat_min, lat_max = 0.0, 10.0
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SpatialExtent(
                lon_min=lon_min,
                lon_max=lon_max,
                lat_min=lat_min,
                lat_max=lat_max
            )
        
        assert "less than or equal to 180" in str(exc_info.value)

    def test_spatial_extent_lat_min_below_minimum(self):
        """Test SpatialExtent with latitude minimum below -90."""
        # Arrange
        lon_min, lon_max = 0.0, 10.0
        lat_min = -91.0
        lat_max = 0.0
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SpatialExtent(
                lon_min=lon_min,
                lon_max=lon_max,
                lat_min=lat_min,
                lat_max=lat_max
            )
        
        assert "greater than or equal to -90" in str(exc_info.value)

    def test_spatial_extent_lat_max_above_maximum(self):
        """Test SpatialExtent with latitude maximum above 90."""
        # Arrange
        lon_min, lon_max = 0.0, 10.0
        lat_min = 0.0
        lat_max = 91.0
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SpatialExtent(
                lon_min=lon_min,
                lon_max=lon_max,
                lat_min=lat_min,
                lat_max=lat_max
            )
        
        assert "less than or equal to 90" in str(exc_info.value)

    def test_spatial_extent_lon_max_less_than_lon_min(self):
        """Test SpatialExtent with lon_max less than lon_min."""
        # Arrange
        lon_min = 10.0
        lon_max = 5.0
        lat_min, lat_max = 0.0, 10.0
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SpatialExtent(
                lon_min=lon_min,
                lon_max=lon_max,
                lat_min=lat_min,
                lat_max=lat_max
            )
        
        assert "lon_max (5.0) must be >= lon_min (10.0)" in str(exc_info.value)

    def test_spatial_extent_lon_max_equal_to_lon_min(self):
        """Test SpatialExtent with lon_max equal to lon_min."""
        # Arrange
        lon_min = 5.0
        lon_max = 5.0
        lat_min, lat_max = 0.0, 10.0
        
        # Act
        spatial = SpatialExtent(
            lon_min=lon_min,
            lon_max=lon_max,
            lat_min=lat_min,
            lat_max=lat_max
        )
        
        # Assert
        assert spatial.lon_min == spatial.lon_max == 5.0

    def test_spatial_extent_lat_max_less_than_lat_min(self):
        """Test SpatialExtent with lat_max less than lat_min."""
        # Arrange
        lon_min, lon_max = 0.0, 10.0
        lat_min = 10.0
        lat_max = 5.0
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SpatialExtent(
                lon_min=lon_min,
                lon_max=lon_max,
                lat_min=lat_min,
                lat_max=lat_max
            )
        
        assert "lat_max (5.0) must be > lat_min (10.0)" in str(exc_info.value)

    def test_spatial_extent_lat_max_equal_to_lat_min(self):
        """Test SpatialExtent with lat_max equal to lat_min."""
        # Arrange
        lon_min, lon_max = 0.0, 10.0
        lat_min = 5.0
        lat_max = 5.0
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SpatialExtent(
                lon_min=lon_min,
                lon_max=lon_max,
                lat_min=lat_min,
                lat_max=lat_max
            )
        
        assert "lat_max (5.0) must be > lat_min (5.0)" in str(exc_info.value)


class TestTemporalExtent:
    """Test cases for TemporalExtent class."""

    def test_temporal_extent_happy_path(self):
        """Test TemporalExtent with valid start and end times."""
        # Arrange
        start = datetime(2023, 1, 1, 0, 0, 0)
        end = datetime(2023, 12, 31, 23, 59, 59)
        
        # Act
        temporal = TemporalExtent(start=start, end=end)
        
        # Assert
        assert temporal.start == start
        assert temporal.end == end

    def test_temporal_extent_same_day(self):
        """Test TemporalExtent with start and end on the same day."""
        # Arrange
        start = datetime(2023, 6, 15, 8, 0, 0)
        end = datetime(2023, 6, 15, 17, 0, 0)
        
        # Act
        temporal = TemporalExtent(start=start, end=end)
        
        # Assert
        assert temporal.start == start
        assert temporal.end == end

    def test_temporal_extent_same_time(self):
        """Test TemporalExtent with start and end at the same time."""
        # Arrange
        start = datetime(2023, 6, 15, 12, 0, 0)
        end = datetime(2023, 6, 15, 12, 0, 0)
        
        # Act
        temporal = TemporalExtent(start=start, end=end)
        
        # Assert
        assert temporal.start == start
        assert temporal.end == end

    def test_temporal_extent_end_before_start(self):
        """Test TemporalExtent with end time before start time."""
        # Arrange
        start = datetime(2023, 12, 31, 23, 59, 59)
        end = datetime(2023, 1, 1, 0, 0, 0)
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            TemporalExtent(start=start, end=end)
        
        assert "start" in str(exc_info.value) and "must be before end" in str(exc_info.value)

    def test_temporal_extent_future_dates(self):
        """Test TemporalExtent with future dates."""
        # Arrange
        start = datetime(2030, 1, 1, 0, 0, 0)
        end = datetime(2030, 12, 31, 23, 59, 59)
        
        # Act
        temporal = TemporalExtent(start=start, end=end)
        
        # Assert
        assert temporal.start == start
        assert temporal.end == end

    def test_temporal_extent_past_dates(self):
        """Test TemporalExtent with past dates."""
        # Arrange
        start = datetime(1990, 1, 1, 0, 0, 0)
        end = datetime(1990, 12, 31, 23, 59, 59)
        
        # Act
        temporal = TemporalExtent(start=start, end=end)
        
        # Assert
        assert temporal.start == start
        assert temporal.end == end

    def test_temporal_extent_microsecond_precision(self):
        """Test TemporalExtent with microsecond precision."""
        # Arrange
        start = datetime(2023, 6, 15, 12, 30, 45, 123456)
        end = datetime(2023, 6, 15, 12, 30, 45, 789012)
        
        # Act
        temporal = TemporalExtent(start=start, end=end)
        
        # Assert
        assert temporal.start == start
        assert temporal.end == end

    def test_temporal_extent_timezone_aware(self):
        """Test TemporalExtent with timezone-aware datetime objects."""
        # Arrange
        from datetime import timezone
        start = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2023, 6, 15, 18, 0, 0, tzinfo=timezone.utc)
        
        # Act
        temporal = TemporalExtent(start=start, end=end)
        
        # Assert
        assert temporal.start == start
        assert temporal.end == end


class TestQuery:
    """Test cases for Query class."""

    def test_query_happy_path(self):
        """Test Query with all required fields."""
        # Arrange
        variable = "sea_surface_temperature"
        spatial = SpatialExtent(
            lon_min=-180.0, lon_max=180.0,
            lat_min=-90.0, lat_max=90.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 12, 31)
        )
        sources = ["source1", "source2"]
        options = {"format": "netcdf", "resolution": "0.25"}
        
        # Act
        query = Query(
            variable=variable,
            spatial=spatial,
            temporal=temporal,
            sources=sources,
            options=options
        )
        
        # Assert
        assert query.variable == variable
        assert query.spatial == spatial
        assert query.temporal == temporal
        assert query.sources == sources
        assert query.options == options

    def test_query_minimal_required_fields(self):
        """Test Query with only required fields."""
        # Arrange
        variable = "temperature"
        spatial = SpatialExtent(
            lon_min=0.0, lon_max=10.0,
            lat_min=0.0, lat_max=10.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2)
        )
        sources = ["single_source"]
        
        # Act
        query = Query(
            variable=variable,
            spatial=spatial,
            temporal=temporal,
            sources=sources
        )
        
        # Assert
        assert query.variable == variable
        assert query.spatial == spatial
        assert query.temporal == temporal
        assert query.sources == sources
        assert query.options == {}

    def test_query_default_empty_sources_and_options(self):
        """Test Query with default empty sources and options raises error."""
        # Arrange
        variable = "pressure"
        spatial = SpatialExtent(
            lon_min=-10.0, lon_max=10.0,
            lat_min=-10.0, lat_max=10.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 6, 1),
            end=datetime(2023, 6, 30)
        )
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Query(
                variable=variable,
                spatial=spatial,
                temporal=temporal
            )
        
        assert "At least one data source must be specified" in str(exc_info.value)

    def test_query_empty_string_variable(self):
        """Test Query with empty string variable."""
        # Arrange
        variable = ""
        spatial = SpatialExtent(
            lon_min=0.0, lon_max=1.0,
            lat_min=0.0, lat_max=1.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2)
        )
        sources = ["test_source"]
        
        # Act
        query = Query(
            variable=variable,
            spatial=spatial,
            temporal=temporal,
            sources=sources
        )
        
        # Assert
        assert query.variable == ""

    def test_query_single_source(self):
        """Test Query with single source."""
        # Arrange
        variable = "humidity"
        spatial = SpatialExtent(
            lon_min=0.0, lon_max=5.0,
            lat_min=0.0, lat_max=5.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 3, 1),
            end=datetime(2023, 3, 31)
        )
        sources = ["weather_station"]
        
        # Act
        query = Query(
            variable=variable,
            spatial=spatial,
            temporal=temporal,
            sources=sources
        )
        
        # Assert
        assert len(query.sources) == 1
        assert query.sources[0] == "weather_station"

    def test_query_multiple_sources(self):
        """Test Query with multiple sources."""
        # Arrange
        variable = "wind_speed"
        spatial = SpatialExtent(
            lon_min=-5.0, lon_max=5.0,
            lat_min=-5.0, lat_max=5.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 7, 1),
            end=datetime(2023, 7, 31)
        )
        sources = ["satellite1", "satellite2", "buoy_network", "model_data"]
        
        # Act
        query = Query(
            variable=variable,
            spatial=spatial,
            temporal=temporal,
            sources=sources
        )
        
        # Assert
        assert len(query.sources) == 4
        assert query.sources == sources

    def test_query_complex_options(self):
        """Test Query with complex options dictionary."""
        # Arrange
        variable = "ocean_current"
        spatial = SpatialExtent(
            lon_min=-180.0, lon_max=180.0,
            lat_min=-90.0, lat_max=90.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 12, 31)
        )
        sources = ["ocean_model"]
        options = {
            "format": "netcdf",
            "resolution": 0.1,
            "depth_levels": [0, 10, 20, 50, 100],
            "interpolation": "bilinear",
            "quality_flags": True,
            "metadata": {"author": "test", "version": "1.0"}
        }
        
        # Act
        query = Query(
            variable=variable,
            spatial=spatial,
            temporal=temporal,
            sources=sources,
            options=options
        )
        
        # Assert
        assert query.options == options
        assert query.options["depth_levels"] == [0, 10, 20, 50, 100]
        assert query.options["metadata"]["author"] == "test"

    def test_query_no_sources_raises_error(self):
        """Test Query with empty sources list raises ValidationError."""
        # Arrange
        variable = "temperature"
        spatial = SpatialExtent(
            lon_min=0.0, lon_max=10.0,
            lat_min=0.0, lat_max=10.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2)
        )
        sources = []
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Query(
                variable=variable,
                spatial=spatial,
                temporal=temporal,
                sources=sources
            )
        
        assert "At least one data source must be specified" in str(exc_info.value)

    def test_query_none_sources_raises_error(self):
        """Test Query with None sources raises ValidationError."""
        # Arrange
        variable = "temperature"
        spatial = SpatialExtent(
            lon_min=0.0, lon_max=10.0,
            lat_min=0.0, lat_max=10.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2)
        )
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Query(
                variable=variable,
                spatial=spatial,
                temporal=temporal,
                sources=None
            )
        
        assert "Input should be a valid list" in str(exc_info.value)

    def test_query_invalid_spatial_extent_propagates_error(self):
        """Test Query with invalid spatial extent propagates ValidationError."""
        # Arrange
        variable = "temperature"
        temporal = TemporalExtent(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2)
        )
        sources = ["test_source"]
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            # Invalid spatial extent with lon_max < lon_min
            spatial = SpatialExtent(
                lon_min=10.0, lon_max=5.0,
                lat_min=0.0, lat_max=10.0
            )
            Query(
                variable=variable,
                spatial=spatial,
                temporal=temporal,
                sources=sources
            )
        
        assert "lon_max (5.0) must be >= lon_min (10.0)" in str(exc_info.value)

    def test_query_invalid_temporal_extent_propagates_error(self):
        """Test Query with invalid temporal extent propagates ValidationError."""
        # Arrange
        variable = "temperature"
        spatial = SpatialExtent(
            lon_min=0.0, lon_max=10.0,
            lat_min=0.0, lat_max=10.0
        )
        sources = ["test_source"]
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            # Invalid temporal extent with end before start
            temporal = TemporalExtent(
                start=datetime(2023, 12, 31),
                end=datetime(2023, 1, 1)
            )
            Query(
                variable=variable,
                spatial=spatial,
                temporal=temporal,
                sources=sources
            )
        
        assert "start" in str(exc_info.value) and "must be before end" in str(exc_info.value)

    def test_query_missing_required_field_variable(self):
        """Test Query with missing required variable field."""
        # Arrange
        spatial = SpatialExtent(
            lon_min=0.0, lon_max=10.0,
            lat_min=0.0, lat_max=10.0
        )
        temporal = TemporalExtent(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2)
        )
        sources = ["test_source"]
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Query(
                spatial=spatial,
                temporal=temporal,
                sources=sources
            )
        
        assert "variable" in str(exc_info.value)

    def test_query_missing_required_field_spatial(self):
        """Test Query with missing required spatial field."""
        # Arrange
        variable = "temperature"
        temporal = TemporalExtent(
            start=datetime(2023, 1, 1),
            end=datetime(2023, 1, 2)
        )
        sources = ["test_source"]
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Query(
                variable=variable,
                temporal=temporal,
                sources=sources
            )
        
        assert "spatial" in str(exc_info.value)

    def test_query_missing_required_field_temporal(self):
        """Test Query with missing required temporal field."""
        # Arrange
        variable = "temperature"
        spatial = SpatialExtent(
            lon_min=0.0, lon_max=10.0,
            lat_min=0.0, lat_max=10.0
        )
        sources = ["test_source"]
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            Query(
                variable=variable,
                spatial=spatial,
                sources=sources
            )
        
        assert "temporal" in str(exc_info.value)
