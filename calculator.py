def Calculate(age, gender, height, weight):

    
    height_m = height * 0.3048
    weight_kg = weight

   
    bmi = weight_kg / (height_m ** 2)

    
    healthy_bmi_min = 18.5
    healthy_bmi_max = 25

   
    healthy_weight_min_kg = healthy_bmi_min * (height_m ** 2)
    healthy_weight_max_kg = healthy_bmi_max * (height_m ** 2)



    weight_to_gain = healthy_weight_min_kg - weight

   
    results = {
        'BMI': round(bmi, 2),
        'Healthy BMI Range': f'{healthy_bmi_min} - {healthy_bmi_max}',
        'Healthy Weight for the Height (kgs)': f'{round(healthy_weight_min_kg, 2)} - {round(healthy_weight_max_kg, 2)}',
    }
    
    if weight_to_gain > 0:
        results['Remarks'] = 'Underweight'
        results['Weight to Gain (kgs)'] = round(weight_to_gain, 2)
        
    elif weight_to_gain == 0:
        results['Remarks'] = 'Overweight'
        results['Weight to Lose (kgs)'] = round(weight_to_gain, 2)
    else:
        results['Remarks'] = 'Normalweight'
        
    return results

if __name__ == "__main__":

    age = 25
    gender = 'male'
    height = 5.5
    weight = 45  # in kg

    Calculate(age=age, gender=gender, height=height, weight=weight)
