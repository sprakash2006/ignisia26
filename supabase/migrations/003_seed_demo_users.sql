

UPDATE profiles
SET reports_to = (SELECT id FROM profiles WHERE email = 'arjun@ignisia.com')
WHERE email = 'meera@ignisia.com';


UPDATE profiles
SET reports_to = (SELECT id FROM profiles WHERE email = 'meera@ignisia.com')
WHERE email = 'priya@ignisia.com';


UPDATE profiles
SET reports_to = (SELECT id FROM profiles WHERE email = 'meera@ignisia.com')
WHERE email = 'rahul@ignisia.com';
