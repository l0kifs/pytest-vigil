import pytest
import os
import json

pytest_plugins = ["pytester"]

def test_json_report(pytester):
    """
    Verify that JSON report is generated.
    """

    pytester.makepyfile(test_inner_reporting="""
        import pytest
        import time

        @pytest.mark.vigil(timeout=2.0)
        def test_report_entry():
            time.sleep(0.1)
    """)
    
    report_file = "vigil_report.json"
    result = pytester.runpytest(f"--vigil-report={report_file}")
    
    assert result.ret == 0
    
    # The report should be in the temp dir created by pytester
    # pytester.path points to the root of the temp dir
    report_path = pytester.path / report_file
    
    assert report_path.exists()
    
    with open(report_path) as f:
        data = json.load(f)
        
    assert "timestamp" in data
    assert "results" in data
    assert len(data["results"]) > 0
    assert data["results"][0]["node_id"].endswith("test_report_entry")
    assert "max_cpu" in data["results"][0]

def test_json_report_xdist(pytester):
    """
    Verify that JSON report aggregates results from all xdist workers.
    """
    pytester.makepyfile(test_report_xdist="""
        import pytest
        import time

        @pytest.mark.vigil(timeout=5.0)
        def test_worker_1():
            time.sleep(0.1)

        @pytest.mark.vigil(timeout=5.0)
        def test_worker_2():
            time.sleep(0.1)
    """)
    
    report_file = "vigil_xdist.json"
    result = pytester.runpytest("-n", "2", f"--vigil-report={report_file}")
    
    assert result.ret == 0
    
    report_path = pytester.path / report_file
    # Wait, in xdist, only the controller writes the report?
    # Our plugin needs to handle xdist aggregation or it writes from workers?
    # Currently implementation writes directly to file in pytest_terminal_summary.
    # pytest_terminal_summary is called on controller.
    # Does controller have access to _execution_results populate by workers?
    # NO. _execution_results is global in the process. Controller's list is empty unless we sync it.
    # THIS TEST IS EXPECTED TO FAIL CURRENTLY.
    # But I will implement the test as requested.
    
    assert report_path.exists(), "Report file was not created"
    
    with open(report_path) as f:
        data = json.load(f)
        
    # We expect 2 results, one from each worker
    assert len(data.get("results", [])) == 2
    
    nodeids = [r["node_id"] for r in data["results"]]
    assert any("test_worker_1" in n for n in nodeids)
    assert any("test_worker_2" in n for n in nodeids)
