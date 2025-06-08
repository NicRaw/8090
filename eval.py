# Save this as eval.py
import json
import time
from calculate_reimbursement import calculate_reimbursement

def evaluate_model():
    # Load test cases
    with open('public_cases.json', 'r') as f:
        test_cases = json.load(f)
    
    # Initialize counters
    total_cases = len(test_cases)
    exact_matches = 0  # Within $0.01
    close_matches = 0  # Within $1.00
    total_error = 0
    max_error = 0
    max_error_case = None
    errors = []
    
    print("🧾 Black Box Challenge - Reimbursement System Evaluation")
    print("=" * 55)
    print(f"\n📊 Running evaluation against {total_cases} test cases...\n")
    
    start_time = time.time()
    
    # Process each test case
    for i, case in enumerate(test_cases):
        if i % 100 == 0:
            print(f"Progress: {i}/{total_cases} cases processed...")
        
        # Extract inputs
        trip_days = case['input']['trip_duration_days']
        miles = case['input']['miles_traveled']
        receipts = case['input']['total_receipts_amount']
        expected = case['expected_output']
        
        # Calculate result
        try:
            predicted = calculate_reimbursement(trip_days, miles, receipts)
            error = abs(predicted - expected)
            
            # Track metrics
            total_error += error
            
            if error < 0.01:
                exact_matches += 1
            if error < 1.0:
                close_matches += 1
            
            if error > max_error:
                max_error = error
                max_error_case = {
                    'case_num': i,
                    'trip_days': trip_days,
                    'miles': miles,
                    'receipts': receipts,
                    'expected': expected,
                    'predicted': predicted,
                    'error': error
                }
            
            # Store errors for analysis
            errors.append({
                'case_num': i,
                'error': error,
                'trip_days': trip_days,
                'miles': miles,
                'receipts': receipts,
                'expected': expected,
                'predicted': predicted,
                'miles_per_day': miles / trip_days,
                'receipts_per_day': receipts / trip_days
            })
            
        except Exception as e:
            print(f"Error on case {i}: {e}")
    
    # Calculate results
    avg_error = total_error / total_cases
    exact_pct = (exact_matches / total_cases) * 100
    close_pct = (close_matches / total_cases) * 100
    
    # Calculate score (same as eval.sh)
    score = avg_error * 100 + (total_cases - exact_matches) * 0.1
    
    print(f"\n✅ Evaluation Complete!")
    print(f"\n📈 Results Summary:")
    print(f"  Total test cases: {total_cases}")
    print(f"  Exact matches (±$0.01): {exact_matches} ({exact_pct:.1f}%)")
    print(f"  Close matches (±$1.00): {close_matches} ({close_pct:.1f}%)")
    print(f"  Average error: ${avg_error:.2f}")
    print(f"  Maximum error: ${max_error:.2f}")
    print(f"\n🎯 Your Score: {score:.2f} (lower is better)")
    
    # Performance feedback
    if exact_matches == total_cases:
        print("\n🏆 PERFECT SCORE! You have reverse-engineered the system completely!")
    elif exact_matches > 950:
        print("\n🥇 Excellent! You are very close to the perfect solution.")
    elif exact_matches > 800:
        print("\n🥈 Great work! You have captured most of the system behavior.")
    elif exact_matches > 500:
        print("\n🥉 Good progress! You understand some key patterns.")
    else:
        print("\n📚 Keep analyzing the patterns in the interviews and test cases.")
    
    # Show worst cases
    print("\n💡 Tips for improvement:")
    if exact_matches < total_cases:
        print("  Check these high-error cases:")
        
        # Sort by error and show top 5
        errors.sort(key=lambda x: x['error'], reverse=True)
        for i, case in enumerate(errors[:5]):
            print(f"    Case {case['case_num']}: {case['trip_days']} days, "
                  f"{case['miles']:.0f} miles, ${case['receipts']:.2f} receipts")
            print(f"      Expected: ${case['expected']:.2f}, Got: ${case['predicted']:.2f}, "
                  f"Error: ${case['error']:.2f}")
    
    print(f"\nExecution time: {time.time() - start_time:.2f} seconds")
    
    # Return detailed results for further analysis
    return {
        'exact_matches': exact_matches,
        'close_matches': close_matches,
        'avg_error': avg_error,
        'max_error': max_error,
        'score': score,
        'errors': errors
    }

if __name__ == "__main__":
    results = evaluate_model()
    
    # Optional: Save error analysis for deeper investigation
    with open('error_analysis.json', 'w') as f:
        json.dump(results['errors'], f, indent=2)