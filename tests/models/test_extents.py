import pytest
from datetime import datetime
from pydantic import ValidationError
from rskit.models.extents import SpatialExtent, TemporalExtent


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


